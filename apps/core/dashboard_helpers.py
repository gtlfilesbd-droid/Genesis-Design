from django.db.models import Count, Q
from django.utils import timezone

from apps.core.models import ActivityLog
from apps.designs.models import DesignRequest, DesignStatus
from apps.permissions.services import PermissionService
from apps.projects.models import ProjectStatus


def get_recent_activity(limit=8):
    return ActivityLog.objects.select_related('user').order_by('-created_at')[:limit]


def get_pending_actions(user, limit=5):
    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    designs = DesignRequest.objects.filter(
        current_holder=user
    ).exclude(status__in=terminal).select_related('project', 'drawing_type')[:limit]
    actions = []
    for d in designs:
        action_label = 'Open'
        if d.status == DesignStatus.NEW_REQUEST:
            action_label = 'Acknowledge'
        elif d.status == DesignStatus.ACKNOWLEDGED:
            action_label = 'Assign'
        elif d.status == DesignStatus.UNDER_REVIEW:
            action_label = 'Review'
        elif d.status == DesignStatus.VERIFICATION_PENDING:
            action_label = 'Verify'
        elif d.status in (DesignStatus.ASSIGNED, DesignStatus.CORRECTION_REQUIRED):
            action_label = 'Work'
        actions.append({'design': d, 'action_label': action_label})
    return actions


def get_dashboard_stats(user):
    now = timezone.now()
    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    designs = PermissionService.filter_design_requests(user, DesignRequest.objects.all())
    projects = PermissionService.get_user_projects(user)

    active_projects = projects.filter(status=ProjectStatus.ACTIVE).count()
    running = designs.exclude(status__in=terminal).count()
    overdue = designs.filter(due_date__lt=now).exclude(status__in=terminal).count()
    completed_month = designs.filter(
        status=DesignStatus.COMPLETED,
        completion_date__month=now.month,
        completion_date__year=now.year,
    ).count()

    return {
        'active_projects': active_projects,
        'total_projects': projects.count(),
        'running_designs': running,
        'overdue_designs': overdue,
        'completed_month': completed_month,
        'sla_breached': designs.filter(sla_status='red').exclude(status__in=terminal).count(),
        'trend_active': f'{active_projects} active',
        'trend_running': f'{running} in progress',
        'trend_overdue': 'Action required' if overdue else 'On track',
        'trend_completed': f'{completed_month} this month',
    }


def get_chart_data():
    designs = DesignRequest.objects.all()
    status_counts = {}
    for status, label in DesignStatus.choices:
        if status != DesignStatus.DRAFT:
            status_counts[label] = designs.filter(status=status).count()

    designer_counts = (
        DesignRequest.objects.filter(assigned_designer__isnull=False)
        .exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED])
        .values('assigned_designer__first_name', 'assigned_designer__last_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )
    workload_labels = []
    workload_data = []
    for row in designer_counts:
        name = f"{row['assigned_designer__first_name']} {row['assigned_designer__last_name']}".strip() or 'Unknown'
        workload_labels.append(name)
        workload_data.append(row['count'])

    return {
        'status_labels': list(status_counts.keys()),
        'status_data': list(status_counts.values()),
        'workload_labels': workload_labels,
        'workload_data': workload_data,
    }
