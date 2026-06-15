from django import forms

from apps.accounts.models import UserRole
from apps.core.models import CompanySettings, RolePermission, SLAConfiguration
from apps.designs.models import DrawingType
from apps.notifications.models import NotificationSetting

INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = CompanySettings
        fields = ['company_name', 'tagline', 'address', 'phone', 'email', 'website', 'timezone_name']
        widgets = {f: forms.TextInput(attrs={'class': INPUT}) for f in ['company_name', 'tagline', 'phone', 'website', 'timezone_name']}
        widgets.update({
            'address': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
        })


class DrawingTypeForm(forms.ModelForm):
    class Meta:
        model = DrawingType
        fields = ['name', 'code_prefix', 'default_sla_days', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT}),
            'code_prefix': forms.TextInput(attrs={'class': INPUT}),
            'default_sla_days': forms.NumberInput(attrs={'class': INPUT, 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }


class SLAConfigurationForm(forms.ModelForm):
    class Meta:
        model = SLAConfiguration
        fields = [
            'default_warning_percent', 'escalation_level_1_days',
            'escalation_level_2_days', 'auto_breach_notify', 'count_weekends',
        ]
        widgets = {
            'default_warning_percent': forms.NumberInput(attrs={'class': INPUT, 'min': 1, 'max': 100}),
            'escalation_level_1_days': forms.NumberInput(attrs={'class': INPUT, 'min': 0}),
            'escalation_level_2_days': forms.NumberInput(attrs={'class': INPUT, 'min': 0}),
            'auto_breach_notify': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'count_weekends': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }


class NotificationSettingForm(forms.ModelForm):
    class Meta:
        model = NotificationSetting
        fields = [
            'enable_email', 'enable_in_app', 'enable_whatsapp',
            'enable_sms', 'sla_warning_hours',
        ]
        widgets = {
            'enable_email': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_in_app': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_whatsapp': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_sms': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'sla_warning_hours': forms.NumberInput(attrs={'class': INPUT, 'min': 1}),
        }


class RolePermissionForm(forms.ModelForm):
    class Meta:
        model = RolePermission
        fields = [
            'can_create_project', 'can_create_request', 'can_assign_designer',
            'can_review', 'can_verify', 'can_manage_users', 'can_view_reports',
            'can_manage_settings',
        ]
        widgets = {f: forms.CheckboxInput(attrs={'class': 'rounded'}) for f in [
            'can_create_project', 'can_create_request', 'can_assign_designer',
            'can_review', 'can_verify', 'can_manage_users', 'can_view_reports',
            'can_manage_settings',
        ]}


DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=True,
        can_review=True, can_verify=True, can_manage_users=True,
        can_view_reports=True, can_manage_settings=True,
    ),
    UserRole.HEAD_OF_DESIGN: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=True,
        can_review=True, can_verify=False, can_manage_users=False,
        can_view_reports=True, can_manage_settings=False,
    ),
    UserRole.DESIGNER: dict(
        can_create_project=False, can_create_request=False, can_assign_designer=False,
        can_review=False, can_verify=False, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
    UserRole.VERIFICATION_TEAM: dict(
        can_create_project=False, can_create_request=False, can_assign_designer=False,
        can_review=False, can_verify=True, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
    UserRole.DESIGN_REQUESTER: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=False,
        can_review=False, can_verify=False, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
}


def ensure_role_permissions():
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        RolePermission.objects.update_or_create(role=role, defaults=perms)
