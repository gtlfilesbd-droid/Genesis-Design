from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q
from django.shortcuts import render
from django.utils import timezone

from apps.permissions.decorators import require_global_permission
from apps.permissions.services import PermissionService
from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus, DeadlineStatus
from apps.projects.models import Project, ProjectStatus


def compute_designer_kpis(designer):
    designs = DesignRequest.objects.filter(assigned_designer=designer)
    assigned = designs.count()
    completed_qs = designs.filter(status=DesignStatus.COMPLETED)
    completed = completed_qs.count()
    on_time = designs.filter(
        status=DesignStatus.COMPLETED,
        completion_date__lte=F('due_date'),
    ).count()
    late = completed - on_time
    corrections = designs.filter(revision_count__gt=0).count()
    first_time = completed - corrections if completed > corrections else 0

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]

    durations = []
    fastest = None
    slowest = None
    for design in completed_qs.filter(completion_date__isnull=False).select_related('project'):
        assignment = design.assignments.order_by('assigned_at').first()
        if assignment and design.completion_date:
            days = (design.completion_date - assignment.assigned_at).total_seconds() / 86400
            durations.append(days)
            if fastest is None or days < fastest:
                fastest = days
            if slowest is None or days > slowest:
                slowest = days
    avg_completion_days = round(sum(durations) / len(durations), 1) if durations else None

    return {
        'total_assigned': assigned,
        'total_completed': completed,
        'on_time_rate': round((on_time / completed * 100) if completed else 0, 1),
        'late_rate': round((late / completed * 100) if completed else 0, 1),
        'total_corrections': corrections,
        'first_time_approval_rate': round((first_time / completed * 100) if completed else 0, 1),
        'completion_rate': round((completed / assigned * 100) if assigned else 0, 1),
        'avg_completion_days': avg_completion_days,
        'in_progress': designs.filter(status=DesignStatus.IN_PROGRESS).count(),
        'overdue': designs.filter(
            due_date__lt=now,
        ).exclude(status__in=terminal).count(),
        'monthly_output': completed_qs.filter(completion_date__gte=month_start).count(),
        'yearly_output': completed_qs.filter(completion_date__gte=year_start).count(),
        'fastest_days': round(fastest, 1) if fastest is not None else None,
        'slowest_days': round(slowest, 1) if slowest is not None else None,
    }


def compute_hod_kpis(hod):
    designs = DesignRequest.objects.all()
    managed = designs.count()
    approved = designs.filter(status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED]).count()
    corrections = designs.filter(revision_count__gt=0).count()
    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    active = designs.exclude(status__in=terminal)
    overdue = active.filter(due_date__lt=timezone.now()).count()

    return {
        'total_managed': managed,
        'approved': approved,
        'active_pipeline': active.count(),
        'overdue': overdue,
        'cancelled': designs.filter(status=DesignStatus.CANCELLED).count(),
        'with_designer': active.filter(
            status__in=[
                DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
                DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
            ],
        ).count(),
        'waiting_review': active.filter(status=DesignStatus.UNDER_REVIEW).count(),
        'waiting_verification': active.filter(
            status__in=[
                DesignStatus.VERIFICATION_PENDING_ACK,
                DesignStatus.VERIFICATION_PENDING,
                DesignStatus.VERIFICATION_CORRECTION,
            ],
        ).count(),
        'waiting_compliance': active.filter(
            status__in=[
                DesignStatus.AWAITING_COMPLIANCE,
                DesignStatus.COMPLIANCE_PENDING_ACK,
                DesignStatus.COMPLIANCE_PENDING,
                DesignStatus.COMPLIANCE_CORRECTION,
            ],
        ).count(),
        'waiting_approval': active.filter(status=DesignStatus.FINAL_APPROVAL_PENDING).count(),
        'approval_rate': round((approved / managed * 100) if managed else 0, 1),
        'correction_rate': round((corrections / managed * 100) if managed else 0, 1),
        'overdue_percentage': round((overdue / managed * 100) if managed else 0, 1),
    }


def compute_verification_kpis(verifier):
    from apps.core.dashboard_helpers import _avg_stage_hours

    reviewed = DesignRequest.objects.filter(
        Q(verified_by=verifier) | Q(assigned_verifier=verifier),
    ).distinct()
    total = reviewed.count()
    approved = reviewed.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED, DesignStatus.AWAITING_COMPLIANCE],
    ).count()
    corrections = reviewed.filter(revision_count__gt=0).count()
    pending = DesignRequest.objects.filter(
        Q(assigned_verifier=verifier) | Q(verified_by=verifier),
        status__in=[
            DesignStatus.VERIFICATION_PENDING_ACK,
            DesignStatus.VERIFICATION_PENDING,
        ],
    ).distinct().count()
    corrections_sent = reviewed.filter(status=DesignStatus.VERIFICATION_CORRECTION).count()

    return {
        'total_verified': total,
        'approved': approved,
        'pending': pending,
        'corrections_sent': corrections_sent,
        'accuracy_rate': round((approved / total * 100) if total else 0, 1),
        'correction_rate': round((corrections / total * 100) if total else 0, 1),
        'avg_verification_hours': _avg_stage_hours(DesignStatus.VERIFICATION_PENDING),
    }


def compute_compliance_kpis(officer):
    from apps.core.dashboard_helpers import _avg_stage_hours

    reviewed = DesignRequest.objects.filter(
        Q(approved_by_compliance=officer) | Q(assigned_compliance_officer=officer),
    ).distinct()
    total = reviewed.count()
    approved = reviewed.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
    ).count()
    corrections = reviewed.filter(status=DesignStatus.COMPLIANCE_CORRECTION).count()
    pending = DesignRequest.objects.filter(
        Q(assigned_compliance_officer=officer) | Q(approved_by_compliance=officer),
        status__in=[
            DesignStatus.COMPLIANCE_PENDING_ACK,
            DesignStatus.COMPLIANCE_PENDING,
        ],
    ).distinct().count()
    corrections_sent = reviewed.filter(status=DesignStatus.COMPLIANCE_CORRECTION).count()

    return {
        'total_reviewed': total,
        'approved': approved,
        'pending': pending,
        'corrections_sent': corrections_sent,
        'accuracy_rate': round((approved / total * 100) if total else 0, 1),
        'correction_rate': round((corrections / total * 100) if total else 0, 1),
        'avg_review_hours': _avg_stage_hours(DesignStatus.COMPLIANCE_PENDING),
    }


def compute_requester_kpis(requester):
    requests = DesignRequest.objects.filter(requested_by=requester)
    total_requests = requests.count()
    completed = requests.filter(status=DesignStatus.COMPLETED).count()
    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    active = requests.exclude(status__in=terminal)
    in_progress = active.count()
    pending = in_progress
    overdue_requests = active.filter(due_date__lt=timezone.now()).count()

    return {
        'total_requests': total_requests,
        'completed_requests': completed,
        'in_progress': in_progress,
        'pending_requests': pending,
        'cancelled_requests': requests.filter(status=DesignStatus.CANCELLED).count(),
        'overdue_requests': overdue_requests,
        'approved_requests': requests.filter(
            status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
        ).count(),
        'completion_rate': round((completed / total_requests * 100) if total_requests else 0, 1),
        'overdue_rate': round((overdue_requests / in_progress * 100) if in_progress else 0, 1),
    }


def compute_project_health(project):
    designs = project.design_requests.all()
    total = designs.count()
    if total == 0:
        return 100

    completed = designs.filter(status=DesignStatus.COMPLETED).count()
    overdue = designs.filter(
        due_date__lt=timezone.now()
    ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count()
    corrections = designs.aggregate(s=Count('id', filter=Q(revision_count__gt=0)))['s']
    deadline_missed = designs.filter(deadline_status=DeadlineStatus.RED).count()

    completion_score = (completed / total) * 40
    overdue_penalty = min((overdue / total) * 30, 30)
    correction_penalty = min((corrections / total) * 20, 20)
    deadline_penalty = min((deadline_missed / total) * 10, 10)

    score = max(0, round(completion_score + 40 - overdue_penalty - correction_penalty - deadline_penalty))
    return score


LEADERBOARD_MIN_COMPLETIONS = 3


def _normalize_period(period):
    if period in ('all-time', 'all_time', 'all'):
        return 'all_time'
    if period == 'yearly':
        return 'yearly'
    return 'monthly'


def _period_start(period):
    period = _normalize_period(period)
    now = timezone.now()
    if period == 'yearly':
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == 'monthly':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def compute_leaderboard_kpis(designer, period='monthly'):
    period = _normalize_period(period)
    period_start = _period_start(period)
    designs = DesignRequest.objects.filter(assigned_designer=designer)
    if period_start:
        designs = designs.filter(
            Q(completion_date__gte=period_start) |
            Q(assignments__assigned_at__gte=period_start),
        ).distinct()

    assigned = designs.count()
    completed_qs = designs.filter(status=DesignStatus.COMPLETED)
    if period_start:
        completed_qs = completed_qs.filter(completion_date__gte=period_start)
    completed = completed_qs.count()
    on_time = completed_qs.filter(completion_date__lte=F('due_date')).count()
    corrections = designs.filter(revision_count__gt=0).count()
    first_time = completed - corrections if completed > corrections else 0

    return {
        'total_assigned': assigned,
        'total_completed': completed,
        'on_time_rate': round((on_time / completed * 100) if completed else 0, 1),
        'total_corrections': corrections,
        'first_time_approval_rate': round((first_time / completed * 100) if completed else 0, 1),
        'completion_rate': round((completed / assigned * 100) if assigned else 0, 1),
    }


def get_leaderboard(period='monthly'):
    period = _normalize_period(period)
    designers = PermissionService.get_design_team_members()
    qualified = []
    unqualified = []
    for d in designers:
        kpis = compute_leaderboard_kpis(d, period)
        score = (
            kpis['completion_rate'] * 0.4 +
            kpis['on_time_rate'] * 0.3 +
            kpis['first_time_approval_rate'] * 0.3
        )
        entry = {
            'user': d,
            'score': round(score, 1),
            'kpis': kpis,
            'is_qualified': kpis['total_completed'] >= LEADERBOARD_MIN_COMPLETIONS,
        }
        if entry['is_qualified']:
            qualified.append(entry)
        else:
            unqualified.append(entry)

    qualified.sort(key=lambda x: x['score'], reverse=True)
    unqualified.sort(key=lambda x: x['kpis']['total_completed'], reverse=True)

    return {
        'rankings': qualified + unqualified,
        'below_minimum_count': len(unqualified),
        'min_completions_required': LEADERBOARD_MIN_COMPLETIONS,
        'period': period,
    }


def detect_bottlenecks():
    now = timezone.now()
    slow_designers = []
    for d in PermissionService.get_design_team_members():
        overdue = DesignRequest.objects.filter(
            assigned_designer=d,
            due_date__lt=now,
        ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count()
        if overdue >= 2:
            slow_designers.append({'user': d, 'overdue_count': overdue})

    slow_verifiers = []
    for v in User.objects.filter(role=UserRole.VERIFICATION_TEAM, is_active=True):
        pending = DesignRequest.objects.filter(
            current_holder=v,
            status=DesignStatus.VERIFICATION_PENDING,
            updated_at__lt=now - timedelta(days=3),
        ).count()
        if pending >= 1:
            slow_verifiers.append({'user': v, 'pending_count': pending})

    slow_compliance = []
    for c in User.objects.filter(role=UserRole.COMPLIANCE_TEAM, is_active=True):
        pending = DesignRequest.objects.filter(
            current_holder=c,
            status=DesignStatus.COMPLIANCE_PENDING,
            updated_at__lt=now - timedelta(days=3),
        ).count()
        if pending >= 1:
            slow_compliance.append({'user': c, 'pending_count': pending})

    stalled_projects = []
    for p in Project.objects.filter(status=ProjectStatus.ACTIVE):
        health = compute_project_health(p)
        if health < 50:
            stalled_projects.append({'project': p, 'health': health})

    return {
        'slow_designers': slow_designers,
        'slow_verifiers': slow_verifiers,
        'slow_compliance': slow_compliance,
        'stalled_projects': stalled_projects,
    }


@login_required
def smart_search(request):
    from apps.designs.models import DrawingType
    designs = PermissionService.filter_design_requests(
        request.user,
        DesignRequest.objects.select_related('project', 'drawing_type', 'assigned_designer'),
    )

    q = request.GET.get('q', '')
    drawing_type = request.GET.get('drawing_type')
    project = request.GET.get('project')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    designer = request.GET.get('designer')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if q:
        designs = designs.filter(
            Q(design_number__icontains=q) |
            Q(project__name__icontains=q) |
            Q(project__code__icontains=q)
        )
    if drawing_type:
        designs = designs.filter(drawing_type_id=drawing_type)
    if project:
        designs = designs.filter(project_id=project)
    if status:
        designs = designs.filter(status=status)
    if priority:
        designs = designs.filter(priority=priority)
    if designer:
        designs = designs.filter(assigned_designer_id=designer)
    if date_from:
        designs = designs.filter(created_at__date__gte=date_from)
    if date_to:
        designs = designs.filter(created_at__date__lte=date_to)

    terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    deadline = request.GET.get('deadline')
    if request.GET.get('overdue') and not deadline:
        deadline = 'overdue'
    elif request.GET.get('running') and not deadline:
        deadline = 'running'
    if deadline == 'running':
        designs = designs.exclude(status__in=terminal)
    elif deadline == 'overdue':
        designs = designs.filter(
            due_date__lt=timezone.now(),
        ).exclude(status__in=terminal)

    result_count = designs.count()
    return render(request, 'analytics/search.html', {
        'designs': designs[:100],
        'result_count': result_count,
        'results_truncated': result_count > 100,
        'drawing_types': DrawingType.objects.filter(is_active=True),
        'designers': PermissionService.get_design_team_members(),
        'statuses': DesignStatus.choices,
        'projects': PermissionService.get_search_filter_projects(request.user)[:50],
    })


@login_required
def kpi_dashboard(request):
    from .kpi_display import build_kpi_page_context

    user = request.user
    kpis = {}
    if user.role == UserRole.DESIGNER:
        kpis = compute_designer_kpis(user)
    elif user.role == UserRole.HEAD_OF_DESIGN:
        team_kpis = compute_hod_kpis(user)
        personal = compute_designer_kpis(user)
        kpis = {**team_kpis, **{f'my_{k}': v for k, v in personal.items()}}
    elif user.role == UserRole.VERIFICATION_TEAM:
        kpis = compute_verification_kpis(user)
    elif user.role == UserRole.COMPLIANCE_TEAM:
        kpis = compute_compliance_kpis(user)
    elif user.role == UserRole.DESIGN_REQUESTER:
        kpis = compute_requester_kpis(user)

    context = build_kpi_page_context(user.role, kpis)
    return render(request, 'analytics/kpi.html', {
        'kpi_context': context,
        'role_display': user.get_role_display(),
    })


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def leaderboard(request):
    from .reports_display import build_leaderboard_context

    period = request.GET.get('period', 'monthly')
    leaderboard_data = get_leaderboard(period=period)
    report_context = build_leaderboard_context(
        leaderboard_data['rankings'],
        period=leaderboard_data['period'],
        below_minimum_count=leaderboard_data['below_minimum_count'],
        min_completions_required=leaderboard_data['min_completions_required'],
    )
    return render(request, 'analytics/leaderboard.html', {'report_context': report_context})


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def workload_view(request):
    from .reports_display import build_workload_context

    now = timezone.now()
    active_statuses = [
        DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
        DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
    ]
    terminal_statuses = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
    designers = PermissionService.get_design_team_members().annotate(
        workload=Count('assigned_designs', filter=Q(assigned_designs__status__in=active_statuses)),
        overdue=Count(
            'assigned_designs',
            filter=Q(assigned_designs__due_date__lt=now)
            & ~Q(assigned_designs__status__in=terminal_statuses),
        ),
    ).order_by('workload')
    report_context = build_workload_context(designers)
    return render(request, 'analytics/workload.html', {'report_context': report_context})


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def executive_dashboard(request):
    from .reports_display import build_executive_context

    now = timezone.now()
    projects = Project.objects.all()
    designs = DesignRequest.objects.all()
    terminal_statuses = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]

    active_projects = list(projects.filter(status=ProjectStatus.ACTIVE))
    for p in active_projects:
        p.display_health = compute_project_health(p)

    total_drawings = designs.count()
    completed_drawings = designs.filter(status=DesignStatus.COMPLETED).count()
    pending_drawings = designs.exclude(status__in=terminal_statuses).count()
    overdue_drawings = designs.filter(
        due_date__lt=now,
    ).exclude(status__in=terminal_statuses).count()
    active_pipeline = pending_drawings or 1
    completion_rate = round(completed_drawings / total_drawings * 100, 1) if total_drawings else 0
    on_track_rate = round(100 - (overdue_drawings / active_pipeline * 100), 1)
    portfolio_health = (
        round(sum(p.display_health for p in active_projects) / len(active_projects), 1)
        if active_projects else 0
    )

    at_risk_projects = sum(1 for p in active_projects if p.display_health < 70)

    bottlenecks = detect_bottlenecks()
    leaderboard_top = get_leaderboard()['rankings'][:5]

    raw_context = {
        'total_projects': projects.count(),
        'total_drawings': total_drawings,
        'completed_drawings': completed_drawings,
        'pending_drawings': pending_drawings,
        'overdue_drawings': overdue_drawings,
        'completion_rate': completion_rate,
        'on_track_rate': on_track_rate,
        'portfolio_health': portfolio_health,
        'at_risk_projects': at_risk_projects,
        'active_projects': active_projects,
        'top_performers': leaderboard_top,
        'bottlenecks': bottlenecks,
        'design_team_count': PermissionService.get_design_team_members().count(),
        'verification_team_count': User.objects.filter(
            role=UserRole.VERIFICATION_TEAM, is_active=True
        ).count(),
        'compliance_team_count': User.objects.filter(
            role=UserRole.COMPLIANCE_TEAM, is_active=True
        ).count(),
    }
    report_context = build_executive_context(raw_context)
    return render(request, 'analytics/executive.html', {'report_context': report_context})
