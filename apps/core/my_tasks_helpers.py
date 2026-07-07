from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Case, IntegerField, Q, When
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.designs.models import ComplianceReview, DesignRequest, DesignStatus, Verification
from apps.workflow.action_sla import (
    _compliance_action_overdue_q,
    _designer_action_overdue_q,
    _engineer_overdue_q,
    _hod_action_overdue_q,
    _verification_action_overdue_q,
)

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

SITE_ENGINEER_ACTIVE_STATUSES = [
    DesignStatus.ENGINEER_PENDING_ACK,
    DesignStatus.ENGINEER_IN_PROGRESS,
]

DESIGNER_WORK_STATUSES = [
    DesignStatus.ASSIGNED,
    DesignStatus.IN_PROGRESS,
    DesignStatus.CORRECTION_REQUIRED,
    DesignStatus.RESUBMITTED,
]

DESIGNER_WORK_OVERDUE_STATUSES = [
    DesignStatus.IN_PROGRESS,
    DesignStatus.CORRECTION_REQUIRED,
    DesignStatus.RESUBMITTED,
]

HOD_HOLDER_DUE_OVERDUE_STATUSES = [
    DesignStatus.APPROVED,
    DesignStatus.FINAL_APPROVAL_PENDING,
]

HOD_HOLDER_ACTION_STATUSES = [
    DesignStatus.NEW_REQUEST,
    DesignStatus.ACKNOWLEDGED,
    DesignStatus.SUBMITTED,
    DesignStatus.UNDER_REVIEW,
    DesignStatus.VERIFICATION_CORRECTION,
    DesignStatus.AWAITING_COMPLIANCE,
    DesignStatus.COMPLIANCE_CORRECTION,
    DesignStatus.FINAL_APPROVAL_PENDING,
    DesignStatus.APPROVED,
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


def _designer_work_q(user):
    return Q(assigned_designer=user, status__in=DESIGNER_WORK_STATUSES)


def _hod_holder_action_q(user):
    return Q(current_holder=user, status__in=HOD_HOLDER_ACTION_STATUSES)


def _hod_actionable_q(user):
    return _hod_holder_action_q(user) | _designer_work_q(user)


def _hod_overdue_q(user, now, today):
    return (
        _hod_action_overdue_q(user, now)
        | Q(
            assigned_designer=user,
            status__in=DESIGNER_WORK_OVERDUE_STATUSES,
            due_date__isnull=False,
            due_date__lt=now,
        )
        | Q(
            current_holder=user,
            status__in=HOD_HOLDER_DUE_OVERDUE_STATUSES,
            due_date__isnull=False,
            due_date__lt=now,
        )
    )


def _designer_overdue_q(user, now):
    return (
        _designer_action_overdue_q(user, now)
        | Q(
            assigned_designer=user,
            status__in=DESIGNER_WORK_OVERDUE_STATUSES,
            due_date__isnull=False,
            due_date__lt=now,
        )
    )


def _verification_overdue_q(now):
    return (
        _verification_action_overdue_q(now)
        | Q(
            status__in=[
                DesignStatus.VERIFICATION_PENDING,
                DesignStatus.VERIFICATION_CORRECTION,
            ],
            verification_due_date__isnull=False,
            verification_due_date__lt=now,
        )
    )


def _compliance_overdue_q(now):
    return (
        _compliance_action_overdue_q(now)
        | Q(
            status__in=[
                DesignStatus.COMPLIANCE_PENDING,
                DesignStatus.COMPLIANCE_CORRECTION,
            ],
            compliance_due_date__isnull=False,
            compliance_due_date__lt=now,
        )
    )


def _hod_active_ordering():
    return (
        Case(
            When(status=DesignStatus.NEW_REQUEST, then=0),
            When(status=DesignStatus.ACKNOWLEDGED, then=1),
            When(status__in=[DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW], then=2),
            default=3,
            output_field=IntegerField(),
        ),
        'created_at',
        '-priority',
        '-updated_at',
    )


def _designer_active_qs(qs, user):
    return qs.filter(assigned_designer=user, status__in=DESIGNER_WORK_STATUSES)


def _hod_active_qs(qs, user):
    return qs.filter(_hod_actionable_q(user)).distinct().exclude(status__in=TERMINAL_STATUSES)


def _finished_by_completion(qs, period_start):
    qs = qs.filter(status=DesignStatus.COMPLETED, completion_date__isnull=False)
    if period_start:
        qs = qs.filter(completion_date__gte=period_start)
    return qs.count()


def _designer_stats_and_querysets(user, now, today, period_start):
    base = DesignRequest.objects.filter(assigned_designer=user)
    active = _designer_active_qs(DesignRequest.objects.all(), user).distinct()
    active_qs = active.select_related('project', 'drawing_type')
    overdue = active.filter(_designer_overdue_q(user, now)).distinct()
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': overdue.count(),
        'finished_designs': _finished_by_completion(base, period_start),
    }
    querysets = {
        'assigned_tasks': active_qs.order_by(
            Case(When(status=DesignStatus.ASSIGNED, then=0), default=1, output_field=IntegerField()),
            'created_at',
            'due_date',
        ),
    }
    return stats, querysets


def _hod_stats_and_querysets(user, now, today, period_start):
    active = _hod_active_qs(DesignRequest.objects.all(), user).distinct()
    active_qs = active.select_related(
        'project', 'drawing_type', 'assigned_designer', 'current_holder',
    )
    finished_base = DesignRequest.objects.filter(
        status=DesignStatus.COMPLETED,
        completion_date__isnull=False,
    ).filter(Q(assigned_designer=user) | Q(assigned_by=user))
    if period_start:
        finished_base = finished_base.filter(completion_date__gte=period_start)
    overdue = active.filter(_hod_overdue_q(user, now, today)).distinct()
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': overdue.count(),
        'finished_designs': finished_base.count(),
    }
    querysets = {
        'active_tasks': active_qs.order_by(*_hod_active_ordering()),
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
    overdue = active.filter(_verification_overdue_q(now))
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': overdue.count(),
        'finished_designs': _verification_finished_count(user, period_start),
    }
    querysets = {
        'active_tasks': active_qs.order_by(
            Case(
                When(status=DesignStatus.VERIFICATION_PENDING_ACK, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            'verification_assigned_at',
            '-priority',
            'verification_due_date',
        ),
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
    overdue = active.filter(_compliance_overdue_q(now))
    stats = {
        'active_projects': active.values('project_id').distinct().count(),
        'running_designs': active.count(),
        'overdue_designs': overdue.count(),
        'finished_designs': _compliance_finished_count(user, period_start),
    }
    querysets = {
        'active_tasks': active_qs.order_by(
            Case(
                When(status=DesignStatus.COMPLIANCE_PENDING_ACK, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            'compliance_assigned_at',
            '-priority',
            'compliance_due_date',
        ),
    }
    return stats, querysets


def get_site_engineer_tasks(user, now):
    """Active site engineer assignments for users with site engineer permission."""
    from apps.permissions.services import PermissionService
    if not PermissionService.is_site_engineer(user):
        return []
    active = DesignRequest.objects.filter(
        Q(assigned_site_engineer=user) | Q(main_design_lead=user) | Q(sub_design_lead=user),
        status__in=SITE_ENGINEER_ACTIVE_STATUSES,
    ).select_related('project', 'drawing_type', 'requested_by').order_by(
        Case(
            When(status=DesignStatus.ENGINEER_PENDING_ACK, then=0),
            default=1,
            output_field=IntegerField(),
        ),
        'engineer_assigned_at',
        '-priority',
        'engineer_due_date',
    )
    return list(active)


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


def get_my_tasks_stats_for_scope(user, scope, period='all'):
    now = timezone.now()
    today = now.date()
    period = normalize_period(period)
    period_start = get_period_start(period, now)

    if scope == 'designer':
        stats, _ = _designer_stats_and_querysets(user, now, today, period_start)
    elif scope == 'hod':
        stats, _ = _hod_stats_and_querysets(user, now, today, period_start)
    elif scope == 'verification':
        stats, _ = _verification_stats_and_querysets(user, now, period_start)
    elif scope == 'compliance':
        stats, _ = _compliance_stats_and_querysets(user, now, period_start)
    elif scope == 'requester':
        stats, _ = _requester_stats_and_querysets(user, today, period_start)
    else:
        stats, _ = _default_stats_and_querysets(user, now, today)
    return stats


def _finished_queryset(qs, period_start):
    qs = qs.filter(status=DesignStatus.COMPLETED, completion_date__isnull=False)
    if period_start:
        qs = qs.filter(completion_date__gte=period_start)
    return qs


def filter_my_tasks_stat(qs, user, scope, stat, period='all'):
    now = timezone.now()
    today = now.date()
    period_start = get_period_start(period, now)

    if scope == 'designer':
        base = qs.filter(assigned_designer=user)
        active = _designer_active_qs(qs, user).distinct()
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(_designer_overdue_q(user, now)).distinct()
        if stat == 'finished':
            return _finished_queryset(base, period_start)

    if scope == 'hod':
        active = _hod_active_qs(qs, user).distinct()
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(_hod_overdue_q(user, now, today)).distinct()
        if stat == 'finished':
            finished = qs.filter(
                status=DesignStatus.COMPLETED,
                completion_date__isnull=False,
            ).filter(Q(assigned_designer=user) | Q(assigned_by=user))
            if period_start:
                finished = finished.filter(completion_date__gte=period_start)
            return finished

    if scope == 'verification':
        base = qs.filter(assigned_verifier=user)
        active = base.filter(status__in=VERIFICATION_ACTIVE_STATUSES)
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(_verification_overdue_q(now))
        if stat == 'finished':
            if period_start:
                return qs.filter(
                    verifications__verifier=user,
                    verifications__action=Verification.VerificationAction.APPROVED,
                    verifications__created_at__gte=period_start,
                ).distinct()
            return qs.filter(
                verified_by=user,
                status__in=VERIFICATION_FINISHED_STATUSES,
            )

    if scope == 'compliance':
        base = qs.filter(assigned_compliance_officer=user)
        active = base.filter(status__in=COMPLIANCE_ACTIVE_STATUSES)
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(_compliance_overdue_q(now))
        if stat == 'finished':
            if period_start:
                return qs.filter(
                    compliance_reviews__reviewer=user,
                    compliance_reviews__action=ComplianceReview.ComplianceAction.APPROVED,
                    compliance_reviews__created_at__gte=period_start,
                ).distinct()
            return qs.filter(
                approved_by_compliance=user,
                status__in=COMPLIANCE_FINISHED_STATUSES,
            )

    if scope == 'requester':
        base = qs.filter(requested_by=user)
        if stat == 'projects_requested':
            if period_start:
                base = base.filter(created_at__gte=period_start)
            return base
        if stat == 'running':
            return base.exclude(status__in=TERMINAL_STATUSES)
        if stat == 'target_overdue':
            return base.exclude(status__in=TERMINAL_STATUSES).filter(
                target_completion_date__isnull=False,
                target_completion_date__lt=today,
            )
        if stat == 'finished':
            return _finished_queryset(base, period_start)

    return qs


def filter_role_overdue_for_list(qs, user, now=None, my_tasks=False):
    """Apply role-appropriate overdue filtering for Design Requests ?overdue=1."""
    now = now or timezone.now()
    view_role = get_my_tasks_view_role(user)
    terminal = TERMINAL_STATUSES

    if view_role == 'requester':
        return filter_my_tasks_stat(qs, user, 'requester', 'target_overdue')
    if view_role == 'hod':
        if my_tasks:
            return filter_my_tasks_stat(qs, user, 'hod', 'overdue')
        return qs.filter(due_date__lt=now).exclude(status__in=terminal)
    if view_role in ('designer', 'verification', 'compliance'):
        return filter_my_tasks_stat(qs, user, view_role, 'overdue')
    return qs.filter(due_date__lt=now).exclude(status__in=terminal)


def filter_role_running_for_list(qs, user):
    view_role = get_my_tasks_view_role(user)
    if view_role == 'default':
        return qs.exclude(status__in=TERMINAL_STATUSES)
    return filter_my_tasks_stat(qs, user, view_role, 'running')


def filter_role_finished_for_list(qs, user, period='all'):
    view_role = get_my_tasks_view_role(user)
    period_start = get_period_start(period)
    if view_role == 'default':
        return _finished_queryset(qs, period_start)
    return filter_my_tasks_stat(qs, user, view_role, 'finished', period)


def filter_role_requested_for_list(qs, user, period='all'):
    return filter_my_tasks_stat(qs, user, 'requester', 'projects_requested', period)


def _my_tasks_list_query(stat, period='all'):
    params = {'my_tasks': '1'}
    if stat in ('active_projects', 'running'):
        params['running'] = '1'
    elif stat in ('overdue', 'target_overdue'):
        params['overdue'] = '1'
    elif stat == 'finished':
        params['finished'] = '1'
    elif stat == 'projects_requested':
        params['requested'] = '1'
    if period and period != 'all':
        params['period'] = period
    return urlencode(params)


def build_my_tasks_request_url(scope, stat, period='all'):
    return f"{reverse('requests:list')}?{_my_tasks_list_query(stat, period)}"


def build_my_tasks_period_urls(stat, active_period='all'):
    urls = {}
    for period in ('week', 'month', 'year', 'all'):
        urls[period] = build_my_tasks_request_url('', stat, period)
    return urls


MY_TASKS_STAT_CARD_DEFS = {
    'designer': [
        {'key': 'active_projects', 'label': 'Active Projects', 'icon': 'folder', 'icon_bg': 'bg-blue-50', 'icon_color': 'text-blue-600'},
        {'key': 'running', 'label': 'Running Designs', 'icon': 'loader', 'icon_bg': 'bg-amber-50', 'icon_color': 'text-amber-600'},
        {'key': 'overdue', 'label': 'Overdue', 'icon': 'alert-triangle', 'icon_bg': 'bg-red-50', 'icon_color': 'text-red-600'},
        {'key': 'finished', 'label': 'Finished', 'icon': 'check-circle', 'icon_bg': 'bg-green-50', 'icon_color': 'text-green-600'},
    ],
    'hod': [
        {'key': 'active_projects', 'label': 'Active Projects', 'icon': 'folder', 'icon_bg': 'bg-blue-50', 'icon_color': 'text-blue-600'},
        {'key': 'running', 'label': 'Running Designs', 'icon': 'loader', 'icon_bg': 'bg-amber-50', 'icon_color': 'text-amber-600'},
        {'key': 'overdue', 'label': 'Overdue', 'icon': 'alert-triangle', 'icon_bg': 'bg-red-50', 'icon_color': 'text-red-600'},
        {'key': 'finished', 'label': 'Finished', 'icon': 'check-circle', 'icon_bg': 'bg-green-50', 'icon_color': 'text-green-600'},
    ],
    'verification': [
        {'key': 'active_projects', 'label': 'Active Projects', 'icon': 'folder', 'icon_bg': 'bg-blue-50', 'icon_color': 'text-blue-600'},
        {'key': 'running', 'label': 'Running Designs', 'icon': 'clock', 'icon_bg': 'bg-amber-50', 'icon_color': 'text-amber-600'},
        {'key': 'overdue', 'label': 'Overdue', 'icon': 'alert-triangle', 'icon_bg': 'bg-red-50', 'icon_color': 'text-red-600'},
        {'key': 'finished', 'label': 'Finished', 'icon': 'check-circle', 'icon_bg': 'bg-green-50', 'icon_color': 'text-green-600'},
    ],
    'compliance': [
        {'key': 'active_projects', 'label': 'Active Projects', 'icon': 'folder', 'icon_bg': 'bg-blue-50', 'icon_color': 'text-blue-600'},
        {'key': 'running', 'label': 'Running Designs', 'icon': 'clock', 'icon_bg': 'bg-amber-50', 'icon_color': 'text-amber-600'},
        {'key': 'overdue', 'label': 'Overdue', 'icon': 'alert-triangle', 'icon_bg': 'bg-red-50', 'icon_color': 'text-red-600'},
        {'key': 'finished', 'label': 'Finished', 'icon': 'check-circle', 'icon_bg': 'bg-green-50', 'icon_color': 'text-green-600'},
    ],
    'requester': [
        {'key': 'projects_requested', 'label': 'Projects Requested', 'icon': 'folder', 'icon_bg': 'bg-blue-50', 'icon_color': 'text-blue-600'},
        {'key': 'running', 'label': 'Running Designs', 'icon': 'loader', 'icon_bg': 'bg-amber-50', 'icon_color': 'text-amber-600'},
        {'key': 'target_overdue', 'label': 'Target Overdue', 'icon': 'alert-triangle', 'icon_bg': 'bg-red-50', 'icon_color': 'text-red-600'},
        {'key': 'finished', 'label': 'Finished', 'icon': 'check-circle', 'icon_bg': 'bg-green-50', 'icon_color': 'text-green-600'},
    ],
}


STAT_VALUE_KEYS = {
    'active_projects': 'active_projects',
    'running': 'running_designs',
    'overdue': 'overdue_designs',
    'finished': 'finished_designs',
    'projects_requested': 'projects_requested',
    'target_overdue': 'target_overdue',
}


def get_my_tasks_stat_cards(scope, stats, period='all', active_stat=None):
    cards = []
    for card_def in MY_TASKS_STAT_CARD_DEFS.get(scope, ()):
        key = card_def['key']
        value_key = STAT_VALUE_KEYS[key]
        cards.append({
            **card_def,
            'value': stats.get(value_key, 0),
            'url': build_my_tasks_request_url(scope, key, period),
            'active': active_stat == key,
            'danger': key in ('overdue', 'target_overdue') and stats.get(value_key, 0),
            'kpi_alert': key in ('overdue', 'target_overdue') and stats.get(value_key, 0),
        })
    return cards
