from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetDoneView, PasswordResetView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
import json

from apps.core.dashboard_helpers import (
    get_chart_data, get_dashboard_stats, get_pending_actions, get_recent_activity,
)
from apps.designs.models import DesignRequest, DesignStatus
from apps.projects.models import Project, ProjectStatus

from apps.permissions.decorators import require_global_permission
from apps.permissions.services import PermissionService

from .models import User, UserRole
from .user_forms import ProfileEditForm


class GenesisLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy(self.request.user.get_dashboard_url_name())


class GenesisLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


class GenesisPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class GenesisPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


@login_required
def dashboard_redirect(request):
    if not PermissionService.has_global_permission(request.user, 'VIS_PERM_DASHBOARD'):
        return redirect('projects:list')
    return redirect(request.user.get_dashboard_url_name())


@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=user)

    designs = DesignRequest.objects.filter(
        Q(requested_by=user) | Q(assigned_designer=user) | Q(current_holder=user)
    ).distinct()
    permissions_profile = PermissionService.get_user_permissions_profile(user)
    context = {
        'profile_user': user,
        'form': form,
        'permissions_profile': permissions_profile,
        'total_projects_created': Project.objects.filter(created_by=user).count(),
        'total_design_requests': designs.filter(requested_by=user).count(),
        'total_assigned_designs': designs.filter(assigned_designer=user).count(),
        'running_tasks': designs.filter(
            assigned_designer=user,
            status__in=[
                DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
                DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
            ],
        ).count(),
        'pending_tasks': designs.filter(current_holder=user).exclude(
            status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED, DesignStatus.APPROVED]
        ).count(),
        'completed_tasks': designs.filter(
            assigned_designer=user, status=DesignStatus.COMPLETED
        ).count(),
        'overdue_tasks': designs.filter(
            assigned_designer=user,
            due_date__lt=timezone.now(),
        ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def admin_dashboard(request):
    context = _base_dashboard_context(request)
    context.update({
        'total_users': User.objects.filter(is_active=True).count(),
        'total_projects': Project.objects.count(),
        'total_designs': DesignRequest.objects.count(),
        'charts': get_chart_data(),
        'show_charts': True,
    })
    context['charts_json'] = json.dumps(context['charts'])
    return render(request, 'accounts/dashboards/admin.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def requester_dashboard(request):
    projects = PermissionService.get_user_projects(request.user)
    designs = PermissionService.filter_design_requests(
        request.user,
        DesignRequest.objects.filter(requested_by=request.user),
    ).select_related('project', 'drawing_type', 'current_holder')[:20]
    context = _base_dashboard_context(request)
    context.update({
        'projects': projects,
        'designs': designs,
        'active_projects': projects.filter(status=ProjectStatus.ACTIVE).count(),
        'completed_projects': projects.filter(status=ProjectStatus.COMPLETED).count(),
    })
    return render(request, 'accounts/dashboards/requester.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def hod_dashboard(request):
    designs = PermissionService.filter_design_requests(
        request.user,
        DesignRequest.objects.exclude(
            status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]
        ),
    ).select_related('project', 'drawing_type', 'assigned_designer', 'current_holder')
    context = _base_dashboard_context(request)
    context.update({
        'new_requests': designs.filter(status=DesignStatus.NEW_REQUEST).count(),
        'waiting_review': designs.filter(status=DesignStatus.UNDER_REVIEW).count(),
        'waiting_verification': designs.filter(status=DesignStatus.VERIFICATION_PENDING).count(),
        'overdue_designs': designs.filter(due_date__lt=timezone.now()).count(),
        'work_queue': designs.order_by('-priority', 'due_date')[:25],
        'charts': get_chart_data(),
        'show_charts': True,
    })
    context['charts_json'] = json.dumps(context['charts'])
    return render(request, 'accounts/dashboards/hod.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def designer_dashboard(request):
    designs = DesignRequest.objects.filter(
        assigned_designer=request.user
    ).select_related('project', 'drawing_type')
    context = _base_dashboard_context(request)
    context.update({
        'assigned_total': designs.count(),
        'running': designs.filter(status=DesignStatus.IN_PROGRESS).count(),
        'corrections': designs.filter(status=DesignStatus.CORRECTION_REQUIRED).count(),
        'completed': designs.filter(status=DesignStatus.COMPLETED).count(),
        'overdue': designs.filter(
            due_date__lt=timezone.now()
        ).exclude(status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]).count(),
        'my_designs': designs.order_by('-updated_at')[:25],
    })
    return render(request, 'accounts/dashboards/designer.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def verification_dashboard(request):
    designs = DesignRequest.objects.filter(
        status__in=[
            DesignStatus.VERIFICATION_PENDING,
            DesignStatus.VERIFICATION_CORRECTION,
        ]
    ).select_related('project', 'drawing_type', 'assigned_designer')
    context = _base_dashboard_context(request)
    context.update({
        'pending': designs.filter(status=DesignStatus.VERIFICATION_PENDING).count(),
        'corrections': designs.filter(status=DesignStatus.VERIFICATION_CORRECTION).count(),
        'approved_total': DesignRequest.objects.filter(
            verified_by=request.user, status__in=[
                DesignStatus.AWAITING_COMPLIANCE,
                DesignStatus.COMPLIANCE_PENDING,
                DesignStatus.COMPLIANCE_CORRECTION,
                DesignStatus.APPROVED,
                DesignStatus.COMPLETED,
            ]
        ).count(),
        'verification_queue': designs.order_by('-priority', 'updated_at')[:25],
    })
    return render(request, 'accounts/dashboards/verification.html', context)


@login_required
@require_global_permission('VIS_PERM_DASHBOARD')
def compliance_dashboard(request):
    designs = DesignRequest.objects.filter(
        status__in=[
            DesignStatus.COMPLIANCE_PENDING,
            DesignStatus.COMPLIANCE_CORRECTION,
        ]
    ).select_related('project', 'drawing_type', 'assigned_designer')
    context = _base_dashboard_context(request)
    context.update({
        'pending': designs.filter(status=DesignStatus.COMPLIANCE_PENDING).count(),
        'corrections': designs.filter(status=DesignStatus.COMPLIANCE_CORRECTION).count(),
        'approved_total': DesignRequest.objects.filter(
            approved_by_compliance=request.user,
            status__in=[DesignStatus.APPROVED, DesignStatus.COMPLETED],
        ).count(),
        'compliance_queue': designs.order_by('-priority', 'updated_at')[:25],
    })
    return render(request, 'accounts/dashboards/compliance.html', context)


def _base_dashboard_context(request):
    stats = get_dashboard_stats(request.user)
    return {
        'user_obj': request.user,
        'pending_count': DesignRequest.objects.filter(current_holder=request.user).exclude(
            status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED]
        ).count(),
        'stats': stats,
        'recent_activity': get_recent_activity(),
        'pending_actions': get_pending_actions(request.user),
        'today': timezone.now(),
    }
