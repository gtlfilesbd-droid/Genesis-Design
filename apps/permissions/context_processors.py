from django.urls import reverse

from apps.accounts.models import UserRole
from apps.designs.models import DesignStatus
from .services import PermissionService


def _build_breadcrumbs(request):
    crumbs = [{'label': 'Home', 'url': reverse('accounts:dashboard')}]
    path = request.path.strip('/')
    parts = path.split('/')
    if not parts or parts == ['']:
        return crumbs

    if parts[0] == 'dashboard':
        crumbs.append({'label': 'Dashboard', 'url': None})
    elif parts[0] == 'projects':
        crumbs.append({'label': 'Projects', 'url': reverse('projects:list')})
        if len(parts) > 1 and parts[1] == 'new':
            crumbs.append({'label': 'New Project', 'url': None})
        elif len(parts) > 3 and parts[2] == 'requests' and parts[3] == 'new':
            crumbs.append({'label': 'New Design Request', 'url': None})
        elif len(parts) > 2 and parts[2] == 'edit':
            crumbs.append({'label': 'Edit Project', 'url': None})
    elif parts[0] == 'requests':
        crumbs.append({'label': 'Design Requests', 'url': reverse('requests:list')})
        if len(parts) > 1 and parts[1].isdigit():
            crumbs.append({'label': 'Request Detail', 'url': None})
    elif parts[0] == 'my-tasks':
        crumbs.append({'label': 'My Tasks', 'url': None})
    elif parts[0] == 'users':
        crumbs.append({'label': 'Team / Users', 'url': reverse('accounts:user_list')})
        if len(parts) > 1 and parts[1] == 'new':
            crumbs.append({'label': 'Add User', 'url': None})
    elif parts[0] == 'settings':
        crumbs.append({'label': 'Settings', 'url': None})
    elif parts[0] == 'designs':
        if parts[-1] == 'library':
            crumbs.append({'label': 'Design Library', 'url': None})
    elif parts[0] == 'analytics' and len(parts) > 1 and parts[1] == 'search':
        crumbs.append({'label': 'Design Library', 'url': None})
    elif parts[0] == 'workflow':
        crumbs.append({'label': 'Workflow Board', 'url': None})
    elif parts[0] == 'reports':
        crumbs.append({'label': 'Reports', 'url': None})

    return crumbs


def user_permissions(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    ps = PermissionService
    project = getattr(request, 'current_project', None)

    nav_main, nav_management, nav_account = ps.get_navigation(user, request)

    ctx = {
        'sidebar_items': ps.get_user_sidebar_items(user),
        'nav_main': nav_main,
        'nav_management': nav_management,
        'nav_account': nav_account,
        'breadcrumbs': _build_breadcrumbs(request),
        'user_permission_labels': ps.get_user_permission_labels(user),
        'can_admin': ps.has_global_permission(user, 'PERM_ADMIN_PANEL'),
        'can_view_reports': ps.has_global_permission(user, 'PERM_VIEW_REPORTS'),
        'can_manage_users': ps.has_global_permission(user, 'PERM_MANAGE_USERS'),
        'can_create_project': ps.has_global_permission(user, 'PROJECT_PERM_CREATE'),
        'can_view_all_projects': ps.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'),
        'can_view_team': ps.has_global_permission(user, 'NAV_PERM_TEAM'),
        'can_view_profiles': ps.has_global_permission(user, 'VIS_PERM_USER_PROFILES'),
        'can_view_workflow': ps.has_global_permission(user, 'NAV_PERM_TASKBOARD'),
        'can_view_dashboard': ps.has_global_permission(user, 'NAV_PERM_DASHBOARD'),
    }

    if project:
        ctx.update({
            'can_edit_project': ps.has_project_permission(user, project, 'PROJECT_PERM_EDIT'),
            'can_request': ps.has_project_permission(user, project, 'PROJECT_PERM_REQUEST'),
            'can_assign': ps.has_project_permission(user, project, 'PROJECT_PERM_ASSIGN'),
            'can_review': ps.has_project_permission(user, project, 'PROJECT_PERM_REVIEW'),
            'can_verify': ps.has_project_permission(user, project, 'PROJECT_PERM_VERIFY'),
            'can_approve': ps.has_project_permission(user, project, 'PROJECT_PERM_APPROVE'),
            'can_complete': ps.has_project_permission(user, project, 'PROJECT_PERM_COMPLETE'),
            'can_do_design_work': ps.has_project_permission(user, project, 'DESIGN_PERM_WORK'),
            'can_upload': ps.has_project_permission(user, project, 'DESIGN_PERM_UPLOAD'),
            'can_revise': ps.has_project_permission(user, project, 'DESIGN_PERM_REVISE'),
            'can_comment': ps.has_project_permission(user, project, 'PROJECT_PERM_COMMENT'),
        })

    current_design = getattr(request, 'current_design', None)
    if current_design:
        design_project = current_design.project
        ctx.update({
            'can_edit_project': ps.has_project_permission(user, design_project, 'PROJECT_PERM_EDIT'),
            'can_request': ps.has_project_permission(user, design_project, 'PROJECT_PERM_REQUEST'),
            'can_assign': ps.has_project_permission(user, design_project, 'PROJECT_PERM_ASSIGN'),
            'can_review': ps.has_project_permission(user, design_project, 'PROJECT_PERM_REVIEW'),
            'can_verify': ps.has_project_permission(user, design_project, 'PROJECT_PERM_VERIFY'),
            'can_approve': ps.has_project_permission(user, design_project, 'PROJECT_PERM_APPROVE'),
            'can_complete': ps.has_project_permission(user, design_project, 'PROJECT_PERM_COMPLETE'),
            'can_do_design_work': ps.has_project_permission(user, design_project, 'DESIGN_PERM_WORK'),
            'can_upload': ps.has_project_permission(user, design_project, 'DESIGN_PERM_UPLOAD'),
            'can_revise': ps.has_project_permission(user, design_project, 'DESIGN_PERM_REVISE'),
            'can_comment': ps.has_project_permission(user, design_project, 'PROJECT_PERM_COMMENT'),
            'can_acknowledge': ps.has_project_permission(user, design_project, 'PROJECT_PERM_ASSIGN'),
            'can_submit_work': (
                current_design.assigned_designer_id == user.pk
                and (
                    ps.has_project_permission(user, design_project, 'DESIGN_PERM_WORK')
                    or user.role in (
                        UserRole.DESIGNER, UserRole.HEAD_OF_DESIGN, UserRole.ADMIN,
                    )
                )
            ),
            'can_cancel_request': (
                current_design.status == DesignStatus.NEW_REQUEST
                and current_design.requested_by_id == user.pk
                and ps.has_project_permission(user, design_project, 'PROJECT_PERM_REQUEST')
            ) or (
                ps.has_global_permission(user, 'PERM_ADMIN_PANEL')
                and current_design.status not in ('completed', 'cancelled')
            ),
        })

    return ctx
