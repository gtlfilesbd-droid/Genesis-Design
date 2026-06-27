from django.db.models import Count, F, Q
from django.utils import timezone

from apps.core.models import ActivityLog, StageDuration
from apps.designs.models import DesignRequest, DesignReview, DesignStatus
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


def _avg_stage_hours(stage):
    durations = StageDuration.objects.filter(
        stage=stage, ended_at__isnull=False,
    ).annotate(
        hours=(F('ended_at') - F('started_at')),
    )
    total_seconds = 0
    count = 0
    for row in durations.values('started_at', 'ended_at'):
        delta = row['ended_at'] - row['started_at']
        total_seconds += delta.total_seconds()
        count += 1
    if not count:
        return None
    return round(total_seconds / count / 3600, 1)


def enrich_review_queue(designs, stage='verification'):
    now = timezone.now()
    enriched = []
    for design in designs:
        if stage == 'compliance':
            anchor = design.compliance_acknowledged_at or design.compliance_assigned_at
        else:
            anchor = design.verification_acknowledged_at or design.verification_assigned_at
        design.pending_days = (now - anchor).days if anchor else 0
        last_review = design.reviews.filter(action='accept').order_by('-created_at').first()
        design.sent_by = last_review.reviewer if last_review else design.assigned_by
        enriched.append(design)
    return enriched


def get_hod_performance():
    designs = DesignRequest.objects.exclude(status=DesignStatus.DRAFT)
    corrections = DesignReview.objects.filter(action='correction').count()
    verification_corrections = designs.filter(
        status=DesignStatus.VERIFICATION_CORRECTION,
    ).count()
    compliance_corrections = designs.filter(
        status=DesignStatus.COMPLIANCE_CORRECTION,
    ).count()
    return {
        'total_managed': designs.count(),
        'total_approved': designs.filter(
            status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
        ).count(),
        'total_cancelled': designs.filter(status=DesignStatus.CANCELLED).count(),
        'total_corrections': corrections + verification_corrections + compliance_corrections,
        'avg_review_hours': _avg_stage_hours(DesignStatus.UNDER_REVIEW),
        'avg_assignment_hours': _avg_stage_hours(DesignStatus.ACKNOWLEDGED),
    }


def get_designer_productivity(designer):
    designs = DesignRequest.objects.filter(assigned_designer=designer)
    completed = designs.filter(status=DesignStatus.COMPLETED, completion_date__isnull=False)
    durations = []
    fastest = None
    slowest = None
    for design in completed.select_related('project'):
        assignment = design.assignments.order_by('assigned_at').first()
        if assignment and design.completion_date:
            days = (design.completion_date - assignment.assigned_at).total_seconds() / 86400
            durations.append(days)
            if fastest is None or days < fastest:
                fastest = days
            if slowest is None or days > slowest:
                slowest = days
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return {
        'avg_completion_days': round(sum(durations) / len(durations), 1) if durations else None,
        'fastest_days': round(fastest, 1) if fastest is not None else None,
        'slowest_days': round(slowest, 1) if slowest is not None else None,
        'monthly_output': completed.filter(completion_date__gte=month_start).count(),
        'yearly_output': completed.filter(completion_date__gte=year_start).count(),
        'rework_count': designs.filter(revision_count__gt=0).count(),
    }


def get_verification_performance(user):
    reviewed = DesignRequest.objects.filter(
        Q(verified_by=user) | Q(assigned_verifier=user),
    ).distinct()
    corrections = reviewed.filter(revision_count__gt=0).count()
    approved = reviewed.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED, DesignStatus.AWAITING_COMPLIANCE],
    ).count()
    return {
        'avg_verification_hours': _avg_stage_hours(DesignStatus.VERIFICATION_PENDING),
        'total_corrections': corrections,
        'total_final_approvals': approved,
        'total_reviewed': reviewed.count(),
    }


def get_compliance_performance(user):
    reviewed = DesignRequest.objects.filter(
        Q(approved_by_compliance=user) | Q(assigned_compliance_officer=user),
    ).distinct()
    corrections = reviewed.filter(status=DesignStatus.COMPLIANCE_CORRECTION).count()
    approved = reviewed.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
    ).count()
    return {
        'avg_review_hours': _avg_stage_hours(DesignStatus.COMPLIANCE_PENDING),
        'total_corrections': corrections,
        'total_final_approvals': approved,
        'total_reviewed': reviewed.count(),
    }
