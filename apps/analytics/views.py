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
    completed = designs.filter(status=DesignStatus.COMPLETED).count()
    on_time = designs.filter(
        status=DesignStatus.COMPLETED,
        completion_date__lte=F('due_date'),
    ).count()
    late = completed - on_time
    corrections = designs.filter(revision_count__gt=0).count()
    first_time = completed - corrections if completed > corrections else 0

    return {
        'total_assigned': assigned,
        'total_completed': completed,
        'on_time_rate': round((on_time / completed * 100) if completed else 0, 1),
        'late_rate': round((late / completed * 100) if completed else 0, 1),
        'total_corrections': corrections,
        'first_time_approval_rate': round((first_time / completed * 100) if completed else 0, 1),
        'completion_rate': round((completed / assigned * 100) if assigned else 0, 1),
    }


def compute_hod_kpis(hod):
    designs = DesignRequest.objects.all()
    managed = designs.count()
    approved = designs.filter(status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED]).count()
    corrections = designs.filter(revision_count__gt=0).count()
    overdue = designs.filter(
        due_date__lt=timezone.now()
    ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count()

    return {
        'total_managed': managed,
        'approved': approved,
        'correction_rate': round((corrections / managed * 100) if managed else 0, 1),
        'overdue_percentage': round((overdue / managed * 100) if managed else 0, 1),
    }


def compute_verification_kpis(verifier):
    verified = DesignRequest.objects.filter(verified_by=verifier)
    total = verified.count()
    approved = verified.filter(status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED]).count()
    corrections = verified.filter(revision_count__gt=0).count()

    return {
        'total_verified': total,
        'approved': approved,
        'accuracy_rate': round((approved / total * 100) if total else 0, 1),
        'correction_rate': round((corrections / total * 100) if total else 0, 1),
    }


def compute_compliance_kpis(officer):
    reviewed = DesignRequest.objects.filter(
        Q(approved_by_compliance=officer) | Q(assigned_compliance_officer=officer),
    ).distinct()
    total = reviewed.count()
    approved = reviewed.filter(
        status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
    ).count()
    corrections = reviewed.filter(status=DesignStatus.COMPLIANCE_CORRECTION).count()

    return {
        'total_reviewed': total,
        'approved': approved,
        'accuracy_rate': round((approved / total * 100) if total else 0, 1),
        'correction_rate': round((corrections / total * 100) if total else 0, 1),
    }


def compute_requester_kpis(requester):
    requests = DesignRequest.objects.filter(requested_by=requester)
    total_requests = requests.count()
    completed = requests.filter(status=DesignStatus.COMPLETED).count()
    pending = requests.exclude(
        status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED],
    ).count()
    projects = PermissionService.get_user_projects(requester)

    return {
        'total_projects': projects.count(),
        'active_projects': projects.filter(status=ProjectStatus.ACTIVE).count(),
        'completed_projects': projects.filter(status=ProjectStatus.COMPLETED).count(),
        'cancelled_projects': projects.filter(status=ProjectStatus.CANCELLED).count(),
        'total_requests': total_requests,
        'completed_requests': completed,
        'pending_requests': pending,
        'completion_rate': round((completed / total_requests * 100) if total_requests else 0, 1),
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


def get_leaderboard(period='monthly'):
    designers = User.objects.filter(role=UserRole.DESIGNER, is_active=True)
    rankings = []
    for d in designers:
        kpis = compute_designer_kpis(d)
        score = (
            kpis['completion_rate'] * 0.4 +
            kpis['on_time_rate'] * 0.3 +
            kpis['first_time_approval_rate'] * 0.3
        )
        rankings.append({
            'user': d,
            'score': round(score, 1),
            'kpis': kpis,
        })
    return sorted(rankings, key=lambda x: x['score'], reverse=True)


def detect_bottlenecks():
    now = timezone.now()
    slow_designers = []
    for d in User.objects.filter(role=UserRole.DESIGNER, is_active=True):
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

    stalled_projects = []
    for p in Project.objects.filter(status=ProjectStatus.ACTIVE):
        health = compute_project_health(p)
        if health < 50:
            stalled_projects.append({'project': p, 'health': health})

    return {
        'slow_designers': slow_designers,
        'slow_verifiers': slow_verifiers,
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

    return render(request, 'analytics/search.html', {
        'designs': designs[:100],
        'drawing_types': DrawingType.objects.filter(is_active=True),
        'designers': User.objects.filter(role=UserRole.DESIGNER, is_active=True),
        'statuses': DesignStatus.choices,
        'projects': PermissionService.get_search_filter_projects(request.user)[:50],
    })


@login_required
def kpi_dashboard(request):
    user = request.user
    kpis = {}
    if user.role == UserRole.DESIGNER:
        kpis = compute_designer_kpis(user)
    elif user.role == UserRole.HEAD_OF_DESIGN:
        kpis = compute_hod_kpis(user)
    elif user.role == UserRole.VERIFICATION_TEAM:
        kpis = compute_verification_kpis(user)
    elif user.role == UserRole.COMPLIANCE_TEAM:
        kpis = compute_compliance_kpis(user)
    elif user.role == UserRole.DESIGN_REQUESTER:
        kpis = compute_requester_kpis(user)

    return render(request, 'analytics/kpi.html', {'kpis': kpis})


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def leaderboard(request):
    rankings = get_leaderboard()
    return render(request, 'analytics/leaderboard.html', {'rankings': rankings})


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def workload_view(request):
    active_statuses = [
        DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
        DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
    ]
    designers = User.objects.filter(
        role=UserRole.DESIGNER, is_active=True
    ).annotate(
        workload=Count('assigned_designs', filter=Q(assigned_designs__status__in=active_statuses))
    ).order_by('workload')
    return render(request, 'analytics/workload.html', {'designers': designers})


@login_required
@require_global_permission('PERM_VIEW_REPORTS')
def executive_dashboard(request):
    now = timezone.now()
    projects = Project.objects.all()
    designs = DesignRequest.objects.all()

    for p in projects.filter(status=ProjectStatus.ACTIVE):
        p.health_score = compute_project_health(p)
        p.save(update_fields=['health_score'])

    bottlenecks = detect_bottlenecks()
    leaderboard_top = get_leaderboard()[:5]

    return render(request, 'analytics/executive.html', {
        'total_projects': projects.count(),
        'total_drawings': designs.count(),
        'pending_drawings': designs.exclude(
            status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]
        ).count(),
        'overdue_drawings': designs.filter(
            due_date__lt=now
        ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count(),
        'at_risk_projects': projects.filter(health_score__lt=70).count(),
        'critical_projects': projects.filter(health_score__lt=50),
        'top_performers': leaderboard_top,
        'bottlenecks': bottlenecks,
        'design_team_count': User.objects.filter(role=UserRole.DESIGNER, is_active=True).count(),
        'verification_team_count': User.objects.filter(
            role=UserRole.VERIFICATION_TEAM, is_active=True
        ).count(),
    })
