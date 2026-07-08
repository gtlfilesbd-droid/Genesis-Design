import json

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.permissions.decorators import require_global_permission, require_project_permission
from apps.permissions.services import PermissionService
from apps.core.models import ActivityLog
from apps.core.middleware import log_audit
from apps.core.utils import log_activity

from .audit_helpers import (
    format_project_timestamp,
    project_audit_snapshot,
    project_changed_fields,
    project_user_display,
)
from .models import Project, ProjectDirector, ProjectEngineer, ProjectStatus


INPUT = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-2.5 text-sm text-slate-900 '
    'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)
TEXTAREA = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-3 text-sm text-slate-900 '
    'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition resize-y'
)
DATE = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-2.5 text-sm text-slate-900 '
    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)
SELECT = (
    'w-full border border-slate-200 rounded-xl bg-white px-4 py-2.5 text-sm text-slate-900 '
    'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary-light transition'
)
EMPTY_SELECT_LABEL = '— Select —'


class ProjectForm(forms.ModelForm):
    client_name = forms.CharField(
        label='Client Name',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'e.g. Essential Clothing Ltd.',
        }),
    )
    code = forms.CharField(
        label='Short Name',
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': INPUT,
            'placeholder': 'e.g. Essential',
        }),
    )

    class Meta:
        model = Project
        fields = [
            'client_name', 'code', 'address',
            'project_director', 'project_engineer',
            'project_coordinator', 'project_manager',
            'start_date', 'expected_completion_date', 'description',
        ]
        widgets = {
            'project_director': forms.Select(attrs={'class': SELECT}),
            'project_engineer': forms.Select(attrs={'class': SELECT}),
            'project_coordinator': forms.Select(attrs={'class': SELECT}),
            'project_manager': forms.Select(attrs={'class': SELECT}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': DATE}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date', 'class': DATE}),
            'address': forms.Textarea(attrs={
                'rows': 2,
                'class': TEXTAREA,
                'placeholder': 'Site or office address (optional)',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': TEXTAREA,
                'placeholder': 'Project scope, notes, or background information for the design team…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].label = 'Address'
        self.fields['address'].required = False
        self.fields['start_date'].label = 'Start Date'
        self.fields['expected_completion_date'].label = 'Expected Completion Date'
        self.fields['expected_completion_date'].required = False
        self.fields['description'].label = 'Description'
        self.fields['description'].required = False

        self.fields['project_director'].label = 'Project Director'
        self.fields['project_director'].required = False
        self.fields['project_director'].empty_label = EMPTY_SELECT_LABEL
        self.fields['project_director'].queryset = ProjectDirector.objects.filter(is_active=True)

        self.fields['project_engineer'].label = 'Project Engineer'
        self.fields['project_engineer'].required = False
        self.fields['project_engineer'].empty_label = EMPTY_SELECT_LABEL
        self.fields['project_engineer'].queryset = ProjectEngineer.objects.filter(is_active=True)

        site_leads = PermissionService.get_site_engineers()
        self._all_site_leads = site_leads

        excluded_from_coordinator = self._user_pk(self.data.get('project_manager')) if self.is_bound else None
        excluded_from_manager = self._user_pk(self.data.get('project_coordinator')) if self.is_bound else None

        self.fields['project_coordinator'].label = 'Project Coordinator'
        self.fields['project_coordinator'].required = False
        self.fields['project_coordinator'].empty_label = EMPTY_SELECT_LABEL
        self.fields['project_coordinator'].queryset = (
            site_leads.exclude(pk=excluded_from_coordinator) if excluded_from_coordinator else site_leads
        )

        self.fields['project_manager'].label = 'Project Manager'
        self.fields['project_manager'].required = False
        self.fields['project_manager'].empty_label = EMPTY_SELECT_LABEL
        self.fields['project_manager'].queryset = (
            site_leads.exclude(pk=excluded_from_manager) if excluded_from_manager else site_leads
        )

    @staticmethod
    def _user_pk(value):
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @property
    def site_lead_options(self):
        return [
            {
                'id': user.pk,
                'name': user.get_full_name().strip() or user.username,
            }
            for user in self._all_site_leads
        ]

    def clean(self):
        cleaned = super().clean()
        coordinator = cleaned.get('project_coordinator')
        manager = cleaned.get('project_manager')
        if coordinator and manager and coordinator.pk == manager.pk:
            msg = 'Project Coordinator and Project Manager cannot be the same user.'
            self.add_error('project_coordinator', msg)
            self.add_error('project_manager', msg)
        return cleaned

    def save(self, commit=True):
        project = super().save(commit=False)
        project.name = project.client_name
        if commit:
            project.save()
        return project


@login_required
@require_global_permission('NAV_PERM_PROJECTS')
def project_list(request):
    qs = PermissionService.get_user_projects(request.user).select_related('created_by')

    status = request.GET.get('status')
    search = request.GET.get('q')
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(code__icontains=search) | Q(client_name__icontains=search)
        )

    return render(request, 'projects/list.html', {
        'projects': qs,
        'statuses': ProjectStatus.choices,
        'active_count': qs.filter(status=ProjectStatus.ACTIVE).count(),
        'total_count': qs.count(),
    })


@login_required
@require_global_permission('PROJECT_PERM_CREATE')
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            now = timezone.now()
            actor = project_user_display(request.user)
            description = (
                f'Project {project.code} created by {actor} on '
                f'{format_project_timestamp(now)}'
            )
            snapshot = project_audit_snapshot(project)
            log_activity(
                'project', project.pk, request.user,
                'project_created', description,
                metadata={'after': snapshot},
            )
            log_audit(
                request.user, 'project_created',
                entity_type='project', entity_id=project.pk,
                after=snapshot,
                comment=description,
                request=request,
            )
            messages.success(request, f'Project {project.code} created successfully.')
            return redirect('projects:detail', pk=project.pk)
        messages.error(request, 'Could not create project. Please check the form and try again.')
    else:
        form = ProjectForm()
    return render(request, 'projects/create.html', {'form': form})


@login_required
@require_global_permission('NAV_PERM_PROJECTS')
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related(
            'created_by', 'updated_by',
            'project_director', 'project_engineer',
            'project_coordinator', 'project_manager',
        ),
        pk=pk,
    )
    if not PermissionService.has_project_permission(request.user, project, 'PROJECT_PERM_VIEW'):
        messages.error(request, 'You do not have access to this project.')
        return redirect('projects:list')

    designs = PermissionService.filter_design_requests(
        request.user,
        project.design_requests.select_related(
            'drawing_type', 'requested_by', 'assigned_designer',
        ),
    )
    logs = ActivityLog.objects.filter(
        Q(entity_type='project', entity_id=project.pk) |
        Q(entity_type='design_request', entity_id__in=designs.values_list('pk', flat=True))
    ).select_related('user').order_by('-created_at')[:50]

    tab = request.GET.get('tab', 'overview')
    status_breakdown = {}
    for d in designs:
        status_breakdown[d.get_status_display()] = status_breakdown.get(d.get_status_display(), 0) + 1

    chart_labels = list(status_breakdown.keys())
    chart_data = list(status_breakdown.values())

    from apps.core.models import CompanySettings
    company = CompanySettings.objects.first()

    return render(request, 'projects/detail.html', {
        'project': project,
        'designs': designs,
        'logs': logs,
        'attachments': project.attachments.all(),
        'legacy_attachment_count': project.attachments.count(),
        'file_sharing_policy': company.file_sharing_policy if company else '',
        'tab': tab,
        'status_breakdown': status_breakdown,
        'completion_pct': round((project.completed_designs / project.total_design_requests * 100) if project.total_design_requests else 0),
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    })


@login_required
@require_project_permission('PROJECT_PERM_EDIT')
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        before = project_audit_snapshot(project)
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)
            project.updated_by = request.user
            project.save()
            after = project_audit_snapshot(project)
            changed = project_changed_fields(before, after)
            actor = project_user_display(request.user)
            now = timezone.now()
            if changed:
                fields_text = ', '.join(changed)
                description = (
                    f'Project {project.code} edited by {actor} on '
                    f'{format_project_timestamp(now)} — changed: {fields_text}'
                )
            else:
                description = (
                    f'Project {project.code} saved by {actor} on '
                    f'{format_project_timestamp(now)} (no field changes)'
                )
            log_activity(
                'project', project.pk, request.user,
                'project_updated', description,
                metadata={'before': before, 'after': after, 'changed_fields': changed},
            )
            log_audit(
                request.user, 'project_updated',
                entity_type='project', entity_id=project.pk,
                before=before, after=after,
                comment=description,
                request=request,
            )
            messages.success(request, 'Project updated successfully.')
            return redirect('projects:detail', pk=project.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/edit.html', {'form': form, 'project': project})
