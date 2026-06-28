from datetime import timedelta
import json

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.permissions.decorators import require_global_permission, require_project_permission
from apps.permissions.services import PermissionService
from apps.core.models import ActivityLog
from apps.core.utils import log_activity

from .models import Project, ProjectStatus


INPUT_CLASS = 'w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

class ProjectForm(forms.ModelForm):
    client_name = forms.CharField(
        label='Client Name',
        max_length=255,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Client / project name'}),
    )
    code = forms.CharField(
        label='Short Name',
        max_length=50,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. PRJ-001'}),
    )

    class Meta:
        model = Project
        fields = [
            'client_name', 'code', 'address',
            'start_date', 'expected_completion_date', 'description',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': INPUT_CLASS}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': INPUT_CLASS}),
        }

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
            log_activity(
                'project', project.pk, request.user,
                'project_created', f'Project {project.code} created',
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
        Project.objects.select_related('created_by'),
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
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            log_activity('project', project.pk, request.user, 'project_updated', f'Project {project.code} updated')
            messages.success(request, 'Project updated successfully.')
            return redirect('projects:detail', pk=project.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/edit.html', {'form': form, 'project': project})
