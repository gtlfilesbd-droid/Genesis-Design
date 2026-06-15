import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.analytics.views import compute_designer_kpis
from apps.core.utils import log_activity
from apps.designs.models import DesignRequest, DesignStatus
from apps.projects.models import Project

from apps.permissions.decorators import require_global_permission
from apps.permissions.services import PermissionService
from .models import User, UserRole, UserStatus
from .user_forms import UserCreateForm, UserEditForm


@login_required
@require_global_permission('PERM_MANAGE_USERS')
def user_list(request):
    users = User.objects.select_related('team', 'manager').annotate(
        running_tasks=Count(
            'assigned_designs',
            filter=Q(assigned_designs__status__in=[
                DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
                DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
            ]),
        ),
        overdue_tasks=Count(
            'assigned_designs',
            filter=Q(
                assigned_designs__due_date__lt=timezone.now(),
                assigned_designs__status__in=[
                    DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
                    DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
                ],
            ),
        ),
    )
    status_filter = request.GET.get('status', 'all')
    role_filter = request.GET.get('role', '')

    if status_filter == 'active':
        users = users.filter(is_active=True, status=UserStatus.ACTIVE)
    elif status_filter == 'inactive':
        users = users.filter(Q(is_active=False) | Q(status=UserStatus.INACTIVE))

    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'users/list.html', {
        'users': users,
        'active_count': User.objects.filter(is_active=True, status=UserStatus.ACTIVE).count(),
        'inactive_count': User.objects.filter(Q(is_active=False) | Q(status=UserStatus.INACTIVE)).count(),
        'total_count': User.objects.count(),
        'roles': UserRole.choices,
        'status_filter': status_filter,
        'create_url': reverse('accounts:user_create'),
    })


@login_required
@require_global_permission('PERM_MANAGE_USERS')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity('user', user.pk, request.user, 'user_created', f'User {user.username} created')
            messages.success(request, f'User {user.get_full_name()} created.')
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = UserCreateForm()
    return render(request, 'users/form.html', {'form': form, 'title': 'Add New User'})


@login_required
@require_global_permission('PERM_MANAGE_USERS')
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save()
            if user.role == UserRole.ADMIN:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            messages.success(request, 'User updated.')
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = UserEditForm(instance=user_obj)
    return render(request, 'users/form.html', {'form': form, 'title': 'Edit User', 'edit_user': user_obj})


@login_required
def user_detail(request, pk):
    user_obj = get_object_or_404(User.objects.select_related('team', 'manager'), pk=pk)
    if (
        request.user.pk != user_obj.pk
        and not PermissionService.has_global_permission(request.user, 'VIS_PERM_USER_PROFILES')
    ):
        messages.error(request, 'Access denied.')
        return redirect('accounts:profile')

    assigned = DesignRequest.objects.filter(assigned_designer=user_obj).select_related('project', 'drawing_type')
    kpis = {}
    if user_obj.role == UserRole.DESIGNER:
        kpis = compute_designer_kpis(user_obj)

    activity = user_obj.activity_logs.select_related('user').order_by('-created_at')[:15]

    monthly_labels = []
    monthly_assigned = []
    monthly_completed = []
    now = timezone.now()
    for i in range(5, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year if now.month - i > 0 else now.year - 1
        monthly_labels.append(f'{year}-{month:02d}')
        monthly_assigned.append(
            DesignRequest.objects.filter(
                assigned_designer=user_obj,
                created_at__month=month, created_at__year=year,
            ).count()
        )
        monthly_completed.append(
            DesignRequest.objects.filter(
                assigned_designer=user_obj,
                status=DesignStatus.COMPLETED,
                completion_date__month=month, completion_date__year=year,
            ).count()
        )

    return render(request, 'users/detail.html', {
        'profile_user': user_obj,
        'assigned_designs': assigned.exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED])[:20],
        'running_tasks': assigned.exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count(),
        'overdue_tasks': assigned.filter(due_date__lt=timezone.now()).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count(),
        'task_queue': assigned.exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).order_by('due_date')[:10],
        'monthly_output': DesignRequest.objects.filter(
            assigned_designer=user_obj, status=DesignStatus.COMPLETED,
            completion_date__month=now.month, completion_date__year=now.year,
        ).count(),
        'kpis': kpis,
        'activity': activity,
        'chart_labels': json.dumps(monthly_labels),
        'chart_assigned': json.dumps(monthly_assigned),
        'chart_completed': json.dumps(monthly_completed),
        'total_projects': Project.objects.filter(created_by=user_obj).count(),
    })


@login_required
@require_global_permission('PERM_MANAGE_USERS')
def user_disable(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.is_active = False
        user_obj.status = UserStatus.INACTIVE
        user_obj.save(update_fields=['is_active', 'status'])
        messages.success(request, f'{user_obj.get_full_name()} has been disabled.')
        return redirect('accounts:user_list')
    return render(request, 'users/confirm_disable.html', {'target_user': user_obj})
