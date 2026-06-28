from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.designs.models import ComplianceReview, DesignRequest, DesignStatus, Verification

TERMINAL_STATUSES = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]

VALID_PERIODS = frozenset({'week', 'month', 'year', 'all'})

PERIOD_OPTIONS = [
    ('week', 'This Week'),
    ('month', 'This Month'),
    ('year', 'This Year'),
    ('all', 'All Time'),
]

VERIFICATION_ACTIVE_STATUSES = [
    DesignStatus.VERIFICATION_PENDING_ACK,
    DesignStatus.VERIFICATION_PENDING,
    DesignStatus.VERIFICATION_CORRECTION,
]

COMPLIANCE_ACTIVE_STATUSES = [
    DesignStatus.COMPLIANCE_PENDING_ACK,
    DesignStatus.COMPLIANCE_PENDING,
    DesignStatus.COMPLIANCE_CORRECTION,
]

VERIFICATION_FINISHED_STATUSES = [
    DesignStatus.AWAITING_COMPLIANCE,
    DesignStatus.COMPLIANCE_PENDING_ACK,
    DesignStatus.COMPLIANCE_PENDING,
    DesignStatus.COMPLIANCE_CORRECTION,
    DesignStatus.APPROVED,
    DesignStatus.COMPLETED,
]

COMPLIANCE_FINISHED_STATUSES = [
    DesignStatus.APPROVED,
    DesignStatus.COMPLETED,
]


def normalize_period(period):
    return period if period in VALID_PERIODS else 'all'


def get_period_start(period, now=None):
    period = normalize_period(period)
    if period == 'all':
        return None
    now = now or timezone.now()
    if period == 'week':
        return now - timedelta(days=7)
    if period == 'month':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == 'year':
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def _hod_involvement_q(user):
    return Q(current_holder=user) | Q(assigned_designer=user)


def _finished_by_completion(qs, period_start):
    qs = qs.filter(status=DesignStatus.COMPLETED, completion_date__isnull=False)
    if period_start:
        qs = qs.filter(completion_date__gte=period_start)
    return qs.count()


def _designer_stats_and_querysets(user, now, today, period_start):
    base = DesignRequest.objects.filter(assigned_designer=user)
    active = base.exclude(status__in=TERMINAL_STATUSES)
    active_qs = active.select_related('project', 'drawing_type')
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': active.filter(
            due_date__isnull=False,
            due_date__lt=now,
        ).count(),
        'finished_designs': _finished_by_completion(base, period_start),
    }
    querysets = {
        'assigned_tasks': active_qs.order_by('due_date'),
    }
    return stats, querysets


def _hod_stats_and_querysets(user, now, today, period_start):
    involvement = _hod_involvement_q(user)
    base = DesignRequest.objects.filter(involvement).distinct()
    active = base.exclude(status__in=TERMINAL_STATUSES)
    active_qs = active.select_related(
        'project', 'drawing_type', 'assigned_designer', 'current_holder',
    )
    overdue_q = Q(due_date__isnull=False, due_date__lt=now) | Q(
        current_holder=user,
        target_completion_date__isnull=False,
        target_completion_date__lt=today,
    )
    finished_base = DesignRequest.objects.filter(
        status=DesignStatus.COMPLETED,
        completion_date__isnull=False,
    ).filter(Q(assigned_designer=user) | Q(assigned_by=user))
    if period_start:
        finished_base = finished_base.filter(completion_date__gte=period_start)
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': active.filter(overdue_q).count(),
        'finished_designs': finished_base.count(),
    }
    querysets = {
        'active_tasks': active_qs.order_by('-priority', 'due_date', '-updated_at'),
    }
    return stats, querysets


def _verification_finished_count(user, period_start):
    if period_start is None:
        return DesignRequest.objects.filter(
            verified_by=user,
            status__in=VERIFICATION_FINISHED_STATUSES,
        ).count()
    return Verification.objects.filter(
        verifier=user,
        action=Verification.VerificationAction.APPROVED,
        created_at__gte=period_start,
    ).count()


def _verification_stats_and_querysets(user, now, period_start):
    base = DesignRequest.objects.filter(assigned_verifier=user)
    active = base.filter(status__in=VERIFICATION_ACTIVE_STATUSES)
    active_qs = active.select_related('project', 'drawing_type', 'assigned_designer')
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': active.filter(
            verification_due_date__isnull=False,
            verification_due_date__lt=now,
        ).count(),
        'finished_designs': _verification_finished_count(user, period_start),
    }
    querysets = {
        'active_tasks': active_qs.order_by('-priority', 'verification_due_date'),
    }
    return stats, querysets


def _compliance_finished_count(user, period_start):
    if period_start is None:
        return DesignRequest.objects.filter(
            approved_by_compliance=user,
            status__in=COMPLIANCE_FINISHED_STATUSES,
        ).count()
    return ComplianceReview.objects.filter(
        reviewer=user,
        action=ComplianceReview.ComplianceAction.APPROVED,
        created_at__gte=period_start,
    ).count()


def _compliance_stats_and_querysets(user, now, period_start):
    base = DesignRequest.objects.filter(assigned_compliance_officer=user)
    active = base.filter(status__in=COMPLIANCE_ACTIVE_STATUSES)
    active_qs = active.select_related('project', 'drawing_type', 'assigned_designer')
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': active.filter(
            compliance_due_date__isnull=False,
            compliance_due_date__lt=now,
        ).count(),
        'finished_designs': _compliance_finished_count(user, period_start),
    }
    querysets = {
        'active_tasks': active_qs.order_by('-priority', 'compliance_due_date'),
    }
    return stats, querysets


def _requester_stats_and_querysets(user, today, period_start):
    base = DesignRequest.objects.filter(requested_by=user)
    active = base.exclude(status__in=TERMINAL_STATUSES)
    active_qs = active.select_related('project', 'drawing_type', 'current_holder')
    projects_qs = base
    if period_start:
        projects_qs = base.filter(created_at__gte=period_start)
    stats = {
        'projects_requested': projects_qs.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'target_overdue': active.filter(
            target_completion_date__isnull=False,
            target_completion_date__lt=today,
        ).count(),
        'finished_designs': _finished_by_completion(base, period_start),
    }
    querysets = {
        'requested_tasks': active_qs.order_by('-created_at'),
    }
    return stats, querysets


def _default_stats_and_querysets(user, now, today):
    terminal = TERMINAL_STATUSES
    assigned = DesignRequest.objects.filter(
        assigned_designer=user,
    ).exclude(status__in=terminal).select_related('project', 'drawing_type')
    held = DesignRequest.objects.filter(
        current_holder=user,
    ).exclude(status__in=terminal).select_related('project', 'drawing_type')
    requested = DesignRequest.objects.filter(
        requested_by=user,
    ).exclude(status__in=terminal).select_related('project', 'drawing_type')

    overdue = assigned.filter(due_date__lt=now)
    due_today = assigned.filter(due_date__date=today)
    due_3d = assigned.filter(
        due_date__date__lte=today + timedelta(days=3),
        due_date__date__gt=today,
    )
    due_7d = assigned.filter(
        due_date__date__lte=today + timedelta(days=7),
        due_date__date__gt=today + timedelta(days=3),
    )
    stats = {
        'overdue_count': overdue.count(),
        'due_today_count': due_today.count(),
        'due_3d_count': due_3d.count(),
        'due_7d_count': due_7d.count(),
    }
    querysets = {
        'assigned_tasks': assigned.order_by('due_date'),
        'held_tasks': held.order_by('-priority', 'due_date'),
        'requested_tasks': requested.order_by('-created_at')[:20],
    }
    return stats, querysets


def get_my_tasks_view_role(user):
    role = user.role
    if role == UserRole.DESIGNER:
        return 'designer'
    if role == UserRole.HEAD_OF_DESIGN:
        return 'hod'
    if role == UserRole.VERIFICATION_TEAM:
        return 'verification'
    if role == UserRole.COMPLIANCE_TEAM:
        return 'compliance'
    if role == UserRole.DESIGN_REQUESTER:
        return 'requester'
    return 'default'


def get_my_tasks_context(user, period='all'):
    now = timezone.now()
    today = now.date()
    period = normalize_period(period)
    period_start = get_period_start(period, now)
    view_role = get_my_tasks_view_role(user)

    if view_role == 'designer':
        stats, querysets = _designer_stats_and_querysets(user, now, today, period_start)
    elif view_role == 'hod':
        stats, querysets = _hod_stats_and_querysets(user, now, today, period_start)
    elif view_role == 'verification':
        stats, querysets = _verification_stats_and_querysets(user, now, period_start)
    elif view_role == 'compliance':
        stats, querysets = _compliance_stats_and_querysets(user, now, period_start)
    elif view_role == 'requester':
        stats, querysets = _requester_stats_and_querysets(user, today, period_start)
    else:
        stats, querysets = _default_stats_and_querysets(user, now, today)

    return view_role, period, stats, querysets
