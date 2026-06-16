from django import forms

from apps.accounts.models import UserRole
from apps.core.models import CompanySettings, RolePermission, DeadlineConfiguration
from apps.designs.models import DrawingType
from apps.notifications.models import NotificationSetting

INPUT = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
DURATION_INPUT = 'w-24 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = CompanySettings
        fields = [
            'company_name', 'tagline', 'address', 'phone', 'email', 'website',
            'timezone_name', 'file_sharing_policy',
        ]
        widgets = {f: forms.TextInput(attrs={'class': INPUT}) for f in ['company_name', 'tagline', 'phone', 'website', 'timezone_name']}
        widgets.update({
            'address': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
            'file_sharing_policy': forms.Textarea(attrs={'class': INPUT, 'rows': 3}),
        })


class DrawingTypeForm(forms.ModelForm):
    class Meta:
        model = DrawingType
        fields = ['name', 'code_prefix', 'allowed_days', 'allowed_hours', 'is_active']
        labels = {
            'allowed_days': 'Allowed days',
            'allowed_hours': 'Allowed hours',
        }
        help_texts = {
            'allowed_days': 'Number of calendar or business days (see Deadline Configuration).',
            'allowed_hours': 'Additional hours added after the allowed days.',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT}),
            'code_prefix': forms.TextInput(attrs={'class': INPUT}),
            'allowed_days': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0}),
            'allowed_hours': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0, 'max': 23}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }


class DeadlineConfigurationForm(forms.ModelForm):
    class Meta:
        model = DeadlineConfiguration
        fields = [
            'default_warning_percent',
            'escalation_level_1_days', 'escalation_level_1_hours',
            'escalation_level_2_days', 'escalation_level_2_hours',
            'escalation_level_3_days', 'escalation_level_3_hours',
            'escalation_level_4_days', 'escalation_level_4_hours',
            'auto_breach_notify', 'count_weekends',
        ]
        labels = {
            'default_warning_percent': 'Warning threshold (%)',
            'escalation_level_1_days': 'Level 1 — days after missed deadline',
            'escalation_level_1_hours': 'Level 1 — hours',
            'escalation_level_2_days': 'Level 2 — days after missed deadline',
            'escalation_level_2_hours': 'Level 2 — hours',
            'escalation_level_3_days': 'Level 3 — days after missed deadline',
            'escalation_level_3_hours': 'Level 3 — hours',
            'escalation_level_4_days': 'Level 4 — days after missed deadline',
            'escalation_level_4_hours': 'Level 4 — hours',
            'auto_breach_notify': 'Auto breach & escalation notifications',
            'count_weekends': 'Count weekends in allowed duration',
        }
        help_texts = {
            'default_warning_percent': 'Yellow warning appears when remaining time falls below this percentage.',
            'escalation_level_1_days': 'Notify assigned designer after this duration from the missed deadline.',
            'escalation_level_2_days': 'Notify Head of Design after this duration from the missed deadline.',
            'escalation_level_3_days': 'Notify designer manager after this duration from the missed deadline.',
            'escalation_level_4_days': 'Notify all admins after this duration from the missed deadline.',
            'count_weekends': 'When enabled, allowed days skip Saturday and Sunday.',
        }
        widgets = {
            'default_warning_percent': forms.NumberInput(attrs={'class': INPUT, 'min': 1, 'max': 100}),
            'escalation_level_1_days': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0}),
            'escalation_level_1_hours': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0, 'max': 23}),
            'escalation_level_2_days': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0}),
            'escalation_level_2_hours': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0, 'max': 23}),
            'escalation_level_3_days': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0}),
            'escalation_level_3_hours': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0, 'max': 23}),
            'escalation_level_4_days': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0}),
            'escalation_level_4_hours': forms.NumberInput(attrs={'class': DURATION_INPUT, 'min': 0, 'max': 23}),
            'auto_breach_notify': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'count_weekends': forms.CheckboxInput(attrs={'class': 'rounded'}),
        }

    def clean(self):
        cleaned = super().clean()
        levels = [
            ('Level 1', cleaned.get('escalation_level_1_days'), cleaned.get('escalation_level_1_hours')),
            ('Level 2', cleaned.get('escalation_level_2_days'), cleaned.get('escalation_level_2_hours')),
            ('Level 3', cleaned.get('escalation_level_3_days'), cleaned.get('escalation_level_3_hours')),
            ('Level 4', cleaned.get('escalation_level_4_days'), cleaned.get('escalation_level_4_hours')),
        ]
        previous_total_hours = -1
        for label, days, hours in levels:
            total_hours = (days or 0) * 24 + (hours or 0)
            if total_hours <= previous_total_hours:
                raise forms.ValidationError(
                    f'{label} escalation must be later than the previous level.'
                )
            previous_total_hours = total_hours
        return cleaned


class NotificationSettingForm(forms.ModelForm):
    class Meta:
        model = NotificationSetting
        fields = [
            'enable_email', 'enable_in_app', 'enable_whatsapp',
            'enable_sms', 'deadline_warning_hours',
        ]
        labels = {
            'deadline_warning_hours': 'Deadline warning lead time (hours)',
        }
        help_texts = {
            'deadline_warning_hours': 'Send a warning notification this many hours before the due date/time.',
        }
        widgets = {
            'enable_email': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_in_app': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_whatsapp': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'enable_sms': forms.CheckboxInput(attrs={'class': 'rounded'}),
            'deadline_warning_hours': forms.NumberInput(attrs={'class': INPUT, 'min': 1}),
        }


class RolePermissionForm(forms.ModelForm):
    class Meta:
        model = RolePermission
        fields = [
            'can_create_project', 'can_create_request', 'can_assign_designer',
            'can_review', 'can_verify', 'can_compliance', 'can_manage_users',
            'can_view_reports', 'can_manage_settings',
        ]
        widgets = {f: forms.CheckboxInput(attrs={'class': 'rounded'}) for f in [
            'can_create_project', 'can_create_request', 'can_assign_designer',
            'can_review', 'can_verify', 'can_compliance', 'can_manage_users',
            'can_view_reports', 'can_manage_settings',
        ]}


DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=True,
        can_review=True, can_verify=True, can_compliance=True, can_manage_users=True,
        can_view_reports=True, can_manage_settings=True,
    ),
    UserRole.HEAD_OF_DESIGN: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=True,
        can_review=True, can_verify=False, can_compliance=False, can_manage_users=False,
        can_view_reports=True, can_manage_settings=False,
    ),
    UserRole.DESIGNER: dict(
        can_create_project=False, can_create_request=False, can_assign_designer=False,
        can_review=False, can_verify=False, can_compliance=False, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
    UserRole.VERIFICATION_TEAM: dict(
        can_create_project=False, can_create_request=False, can_assign_designer=False,
        can_review=False, can_verify=True, can_compliance=False, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
    UserRole.COMPLIANCE_TEAM: dict(
        can_create_project=False, can_create_request=False, can_assign_designer=False,
        can_review=False, can_verify=False, can_compliance=True, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
    UserRole.DESIGN_REQUESTER: dict(
        can_create_project=True, can_create_request=True, can_assign_designer=False,
        can_review=False, can_verify=False, can_compliance=False, can_manage_users=False,
        can_view_reports=False, can_manage_settings=False,
    ),
}


def ensure_role_permissions():
    for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
        RolePermission.objects.update_or_create(role=role, defaults=perms)
