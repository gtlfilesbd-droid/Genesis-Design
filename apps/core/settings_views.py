from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.permissions.decorators import require_global_permission
from apps.accounts.models import UserRole
from apps.designs.models import DrawingType

from .models import CompanySettings, RolePermission, SLAConfiguration
from .settings_forms import (
    CompanySettingsForm,
    DEFAULT_ROLE_PERMISSIONS,
    DrawingTypeForm,
    NotificationSettingForm,
    RolePermissionForm,
    SLAConfigurationForm,
    ensure_role_permissions,
)
from apps.notifications.models import NotificationSetting

SETTINGS_TABS = [
    ('general', 'General', 'settings'),
    ('drawing_types', 'Drawing Types', 'clipboard-list'),
    ('sla', 'SLA Configuration', 'timer'),
    ('notifications', 'Notifications', 'bell'),
    ('company', 'Company Info', 'building-2'),
    ('permissions', 'Role Permissions', 'shield'),
]


@login_required
@require_global_permission('PERM_ADMIN_PANEL')
def settings_index(request):
    tab = request.GET.get('tab', 'general')
    ensure_role_permissions()

    company = CompanySettings.get_solo()
    sla_config = SLAConfiguration.get_solo()
    notif_settings = NotificationSetting.get_solo()
    drawing_types = DrawingType.objects.all()
    role_permissions = [
        {'perm': p, 'label': dict(UserRole.choices).get(p.role, p.role.replace('_', ' ').title())}
        for p in RolePermission.objects.all().order_by('role')
    ]

    if request.method == 'POST':
        action = request.POST.get('action')
        redirect_tab = tab

        if action == 'update_general':
            form = CompanySettingsForm(request.POST, instance=company)
            if form.is_valid():
                form.save()
                messages.success(request, 'General settings saved.')
                redirect_tab = 'general'
        elif action == 'update_company':
            form = CompanySettingsForm(request.POST, instance=company)
            if form.is_valid():
                form.save()
                messages.success(request, 'Company info saved.')
                redirect_tab = 'company'
        elif action == 'update_sla':
            form = SLAConfigurationForm(request.POST, instance=sla_config)
            if form.is_valid():
                form.save()
                messages.success(request, 'SLA configuration saved.')
                redirect_tab = 'sla'
        elif action == 'update_notifications':
            form = NotificationSettingForm(request.POST, instance=notif_settings)
            if form.is_valid():
                form.save()
                messages.success(request, 'Notification settings saved.')
                redirect_tab = 'notifications'
        elif action == 'add_drawing_type':
            form = DrawingTypeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Drawing type added.')
                redirect_tab = 'drawing_types'
        elif action == 'edit_drawing_type':
            dt = DrawingType.objects.get(pk=request.POST.get('drawing_type_id'))
            form = DrawingTypeForm(request.POST, instance=dt)
            if form.is_valid():
                form.save()
                messages.success(request, 'Drawing type updated.')
                redirect_tab = 'drawing_types'
        elif action == 'update_permissions':
            for item in RolePermission.objects.all():
                perm = item
                prefix = f'perm_{perm.pk}_'
                for field in RolePermissionForm.Meta.fields:
                    setattr(perm, field, request.POST.get(f'{prefix}{field}') == 'on')
                perm.save()
            messages.success(request, 'Role permissions updated.')
            redirect_tab = 'permissions'
        elif action == 'reset_permissions':
            for role, defaults in DEFAULT_ROLE_PERMISSIONS.items():
                RolePermission.objects.update_or_create(role=role, defaults=defaults)
            messages.success(request, 'Role permissions reset to defaults.')
            redirect_tab = 'permissions'

        return redirect(f"{reverse('settings:index')}?tab={redirect_tab}")

    return render(request, 'settings/index.html', {
        'tab': tab,
        'settings_tabs': SETTINGS_TABS,
        'company_form': CompanySettingsForm(instance=company),
        'sla_form': SLAConfigurationForm(instance=sla_config),
        'notification_form': NotificationSettingForm(instance=notif_settings),
        'drawing_types': drawing_types,
        'drawing_type_form': DrawingTypeForm(),
        'role_permissions': role_permissions,
        'company': company,
    })
