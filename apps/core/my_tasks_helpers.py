from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Q
from django.urls import reverse
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
        active = base.exclude(status__in=TERMINAL_STATUSES)
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(due_date__isnull=False, due_date__lt=now)
        if stat == 'finished':
            return _finished_queryset(base, period_start)

    if scope == 'hod':
        base = qs.filter(_hod_involvement_q(user)).distinct()
        active = base.exclude(status__in=TERMINAL_STATUSES)
        overdue_q = Q(due_date__isnull=False, due_date__lt=now) | Q(
            current_holder=user,
            target_completion_date__isnull=False,
            target_completion_date__lt=today,
        )
        if stat in ('active_projects', 'running'):
            return active
        if stat == 'overdue':
            return active.filter(overdue_q)
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
            return active.filter(
                verification_due_date__isnull=False,
                verification_due_date__lt=now,
            )
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
            return active.filter(
                compliance_due_date__isnull=False,
                compliance_due_date__lt=now,
            )
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


def build_my_tasks_request_url(scope, stat, period='all'):
    params = {'scope': scope, 'stat': stat}
    if period and period != 'all':
        params['period'] = period
    return f"{reverse('requests:list')}?{urlencode(params)}"


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
        })
    return cards
