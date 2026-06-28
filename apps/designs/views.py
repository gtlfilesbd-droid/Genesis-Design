from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import json

from apps.permissions.decorators import require_global_permission, require_project_permission
from apps.permissions.services import PermissionService
from apps.accounts.models import User, UserRole
from apps.core.my_tasks_helpers import get_my_tasks_context
from apps.core.utils import log_activity
from apps.projects.models import Project

from .forms import DesignRequestForm, create_design_request
from .models import DesignComment, DesignRequest, DesignStatus, DrawingType
from .utils import create_design_comment


@login_required
def design_detail(request, pk):
    design = get_object_or_404(
        DesignRequest.objects.select_related(
            'project', 'drawing_type', 'requested_by',
            'assigned_designer', 'current_holder',
        ),
        pk=pk,
    )
    if not PermissionService.filter_design_requests(request.user).filter(pk=design.pk).exists():
        messages.error(request, 'You do not have access to this design request.')
        return redirect('requests:list')

    if request.method == 'POST' and request.POST.get('action') == 'add_comment':
        if not PermissionService.has_project_permission(request.user, design.project, 'PROJECT_PERM_COMMENT'):
            messages.error(request, 'You do not have permission to comment.')
            return redirect('requests:detail', pk=pk)
        message = request.POST.get('message', '').strip()
        if message:
            create_design_comment(design, request.user, message)
            log_activity('design_request', design.pk, request.user, 'comment_added', message[:100])
            if request.headers.get('HX-Request'):
                comments = design.comments.select_related('author').prefetch_related('mentions')
                return render(request, 'designs/partials/comments.html', {'comments': comments})
            messages.success(request, 'Comment posted.')
        return redirect('requests:detail', pk=pk)

    if request.method == 'POST' and request.POST.get('action') == 'cancel_request':
        if design.requested_by_id != request.user.pk and not PermissionService.has_global_permission(
            request.user, 'PERM_ADMIN_PANEL',
        ):
            messages.error(request, 'You do not have permission to cancel this request.')
            return redirect('requests:detail', pk=pk)
        if (
            design.requested_by_id == request.user.pk
            and design.status != DesignStatus.NEW_REQUEST
        ):
            messages.error(
                request,
                'This request has already been acknowledged and cannot be cancelled.',
            )
            return redirect('requests:detail', pk=pk)
        if design.status not in (DesignStatus.COMPLETED, DesignStatus.CANCELLED):
            old_status = design.status
            design.status = DesignStatus.CANCELLED
            design.save(update_fields=['status', 'primary_status', 'deadline_missed'])
            from apps.core.activity_messages import build_workflow_activity_description
            log_activity(
                'design_request', design.pk, request.user, 'cancelled',
                build_workflow_activity_description('cancelled', request.user, design),
                {'old_status': old_status, 'new_status': DesignStatus.CANCELLED},
            )
            messages.success(request, 'Design request cancelled.')
        return redirect('requests:detail', pk=pk)

    from apps.core.models import ActivityLog, CompanySettings
    logs = ActivityLog.objects.filter(
        entity_type='design_request', entity_id=design.pk
    ).select_related('user')[:50]
    submissions = design.submissions.select_related('submitted_by', 'reviewed_by')
    reviews = design.reviews.select_related('reviewer')
    verifications = design.verifications.select_related('verifier')
    compliance_reviews = design.compliance_reviews.select_related('reviewer')
    attachments = design.attachments.select_related('uploaded_by')
    comments = design.comments.select_related('author').prefetch_related('mentions')
    from apps.workflow.services import compute_delay_attribution
    compute_delay_attribution(design)
    design.refresh_from_db()

    from apps.designs.lifecycle_timeline import build_lifecycle_data

    lifecycle = build_lifecycle_data(design)

    from apps.designs.progress import build_progress_steps
    from apps.workflow.permissions import design_action_flags
    progress_steps, progress_cancelled = build_progress_steps(design)
    action_flags = design_action_flags(request.user, design)
    company = CompanySettings.objects.first()

    return render(request, 'designs/detail.html', {
        'design': design,
        'logs': logs,
        'submissions': submissions,
        'reviews': reviews,
        'verifications': verifications,
        'compliance_reviews': compliance_reviews,
        'attachments': attachments,
        'legacy_attachment_count': attachments.count(),
        'file_sharing_policy': company.file_sharing_policy if company else '',
        'comments': comments,
        'mentionable_users': User.objects.filter(is_active=True).order_by('first_name')[:20],
        'lifecycle': lifecycle,
        'progress_steps': progress_steps,
        'progress_cancelled': progress_cancelled,
        **action_flags,
    })


@login_required
@require_project_permission('PROJECT_PERM_REQUEST')
def design_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = DesignRequestForm(request.POST, project=project)
        if form.is_valid():
            design = create_design_request(project, request.user, form.cleaned_data)
            from apps.notifications.services import NotificationService
            NotificationService.on_request_created(design)
            from apps.workflow.services import get_head_of_design
            hod = get_head_of_design()
            design.current_holder = hod
            design.save(update_fields=['current_holder'])
            from apps.core.activity_messages import (
                build_project_activity_description,
                build_workflow_activity_description,
            )
            log_activity(
                'design_request', design.pk, request.user,
                'design_requested',
                build_workflow_activity_description('design_requested', request.user, design),
                {'drawing_type': design.drawing_type.name},
            )
            log_activity(
                'project', project.pk, request.user,
                'design_requested',
                build_project_activity_description('design_requested', request.user, design),
            )
            messages.success(request, f'Design request {design.design_number} submitted.')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = DesignRequestForm(project=project)
    return render(request, 'designs/create.html', {'form': form, 'project': project})


@login_required
def design_library(request):
    visible_projects = PermissionService.get_user_projects(request.user)
    designs = DesignRequest.objects.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
        project__in=visible_projects,
    ).select_related('project', 'drawing_type', 'assigned_designer', 'requested_by')

    drawing_type = request.GET.get('drawing_type')
    project_code = request.GET.get('project')
    client = request.GET.get('client')
    designer = request.GET.get('designer')

    if drawing_type:
        designs = designs.filter(drawing_type_id=drawing_type)
    if project_code:
        designs = designs.filter(project__code__icontains=project_code)
    if client:
        designs = designs.filter(project__client_name__icontains=client)
    if designer:
        designs = designs.filter(assigned_designer_id=designer)

    return render(request, 'designs/library.html', {
        'designs': designs[:100],
        'drawing_types': DrawingType.objects.filter(is_active=True),
        'designers': PermissionService.get_design_team_members(),
    })


@login_required
def design_request_list(request):
    base_qs = PermissionService.filter_design_requests(
        request.user,
        DesignRequest.objects.select_related(
            'project', 'drawing_type', 'requested_by', 'assigned_designer', 'current_holder'
        ),
    )

    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    now = timezone.now()

    designs = base_qs
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    project = request.GET.get('project')
    search = request.GET.get('q')
    if status:
        designs = designs.filter(status=status)
    if priority:
        designs = designs.filter(priority=priority)
    if project:
        designs = designs.filter(project_id=project)
    if search:
        designs = designs.filter(
            Q(design_number__icontains=search) | Q(project__code__icontains=search)
        )
    if request.GET.get('running'):
        designs = designs.exclude(status__in=terminal)
    if request.GET.get('overdue'):
        designs = designs.filter(due_date__lt=now).exclude(status__in=terminal)
    if request.GET.get('completed_month'):
        designs = designs.filter(
            status=DesignStatus.COMPLETED,
            completion_date__month=now.month,
            completion_date__year=now.year,
        )
    if request.GET.get('mine'):
        designs = designs.filter(assigned_designer=request.user)

    stats = {
        'total': designs.count(),
        'running': designs.exclude(status__in=terminal).count(),
        'overdue': designs.filter(due_date__lt=now).exclude(status__in=terminal).count(),
        'completed_month': designs.filter(
            status=DesignStatus.COMPLETED,
            completion_date__month=now.month,
            completion_date__year=now.year,
        ).count(),
    }

    designs = designs.order_by('-created_at')
    result_count = stats['total']

    status_labels = dict(DesignStatus.choices)
    project_labels = {
        str(p.pk): p.code
        for p in PermissionService.get_user_projects(request.user)[:50]
    }
    priority_labels = {
        'critical': 'Critical',
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low',
    }
    active_filters = []
    if search:
        active_filters.append({'param': 'q', 'label': f'Search: “{search}”'})
    if status:
        active_filters.append({'param': 'status', 'label': status_labels.get(status, status)})
    if priority:
        active_filters.append({'param': 'priority', 'label': priority_labels.get(priority, priority)})
    if project:
        active_filters.append({'param': 'project', 'label': project_labels.get(project, f'Project #{project}')})
    if request.GET.get('running'):
        active_filters.append({'param': 'running', 'label': 'Running only'})
    if request.GET.get('overdue'):
        active_filters.append({'param': 'overdue', 'label': 'Overdue only'})
    if request.GET.get('completed_month'):
        active_filters.append({'param': 'completed_month', 'label': 'Completed this month'})
    if request.GET.get('mine'):
        active_filters.append({'param': 'mine', 'label': 'Assigned to me'})

    has_filters = bool(active_filters)

    active_stat = None
    if request.GET.get('running'):
        active_stat = 'running'
    elif request.GET.get('overdue'):
        active_stat = 'overdue'
    elif request.GET.get('completed_month'):
        active_stat = 'completed_month'
    elif request.GET.get('mine'):
        active_stat = 'mine'
    elif not has_filters:
        active_stat = 'total'

    stat_card_active = {
        'total': active_stat == 'total',
        'running': active_stat == 'running',
        'overdue': active_stat == 'overdue',
        'completed_month': active_stat == 'completed_month',
    }

    return render(request, 'requests/list.html', {
        'designs': designs[:100],
        'result_count': result_count,
        'results_truncated': result_count > 100,
        'statuses': DesignStatus.choices,
        'projects': PermissionService.get_user_projects(request.user)[:50],
        'stats': stats,
        'active_filters': active_filters,
        'has_filters': has_filters,
        'active_stat': active_stat,
        'stat_card_active': stat_card_active,
    })


@login_required
@require_global_permission('NAV_PERM_MY_TASKS')
def my_tasks(request):
    period = request.GET.get('period', 'all')
    task_view, period, stats, querysets = get_my_tasks_context(request.user, period=period)
    return render(request, 'tasks/list.html', {
        'task_view': task_view,
        'period': period,
        'stats': stats,
        'now': timezone.now(),
        'today': timezone.now().date(),
        'user_obj': request.user,
        **querysets,
    })
