from django.db.models import Q
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.core.models import RolePermission
from apps.designs.models import DesignRequest, DesignStatus
from apps.projects.models import Project

ROLE_PERM_FIELDS = {
    'PERM_ADMIN_PANEL': 'can_manage_settings',
    'PERM_MANAGE_USERS': 'can_manage_users',
    'PERM_VIEW_REPORTS': 'can_view_reports',
    'PROJECT_PERM_CREATE': 'can_create_project',
    'PROJECT_PERM_REQUEST': 'can_create_request',
    'PROJECT_PERM_ASSIGN': 'can_assign_designer',
    'PROJECT_PERM_REVIEW': 'can_review',
    'PROJECT_PERM_VERIFY': 'can_verify',
    'PROJECT_PERM_COMPLIANCE': 'can_compliance',
    'PROJECT_PERM_APPROVE': 'can_review',
    'PROJECT_PERM_COMPLETE': 'can_assign_designer',
}

VERIFICATION_STATUSES = [
    DesignStatus.VERIFICATION_PENDING,
    DesignStatus.VERIFICATION_CORRECTION,
]

COMPLIANCE_STATUSES = [
    DesignStatus.AWAITING_COMPLIANCE,
    DesignStatus.COMPLIANCE_PENDING,
    DesignStatus.COMPLIANCE_CORRECTION,
]

ROLE_PERMISSION_LABELS = {
    'can_create_project': 'Create Projects',
    'can_create_request': 'Submit Requests',
    'can_assign_designer': 'Assign Designers',
    'can_review': 'Review Designs',
    'can_verify': 'Verify Designs',
    'can_compliance': 'Compliance Review',
    'can_manage_users': 'Manage Users',
    'can_view_reports': 'View Reports',
    'can_manage_settings': 'Manage Settings',
}


class PermissionService:
    """Role-based permission checks via User.role and RolePermission matrix."""

    @staticmethod
    def _get_role_perms(user):
        if not user or not user.is_authenticated:
            return None
        cache_attr = '_cached_role_perms'
        if not hasattr(user, cache_attr):
            try:
                setattr(user, cache_attr, RolePermission.objects.get(role=user.role))
            except RolePermission.DoesNotExist:
                setattr(user, cache_attr, None)
        return getattr(user, cache_attr)

    @staticmethod
    def _role_flag(user, field_name: str) -> bool:
        perms = PermissionService._get_role_perms(user)
        if not perms:
            return False
        return bool(getattr(perms, field_name, False))

    @staticmethod
    def _extra_flag(user, field_name: str) -> bool:
        try:
            extra = user.extra_permissions
        except Exception:
            return False
        return bool(getattr(extra, field_name, False))

    @staticmethod
    def _matrix_flag(user, field_name: str) -> bool:
        return (
            PermissionService._role_flag(user, field_name)
            or PermissionService._extra_flag(user, field_name)
        )

    @staticmethod
    def _is_admin_or_hod(user) -> bool:
        return (
            user.is_superuser
            or user.role in (UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
        )

    @staticmethod
    def has_global_permission(user, permission_code: str) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        if permission_code == 'PERM_VIEW_ALL_PROJECTS':
            return PermissionService._is_admin_or_hod(user)

        if permission_code in ('VIS_PERM_DASHBOARD', 'VIS_PERM_NOTIFICATIONS'):
            return user.is_active and getattr(user, 'status', 'active') == 'active'

        if permission_code == 'VIS_PERM_WORKFLOW_BOARD':
            return (
                user.role in (UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
                or PermissionService._matrix_flag(user, 'can_assign_designer')
            )

        if permission_code == 'VIS_PERM_TEAM_PAGE':
            return (
                PermissionService._matrix_flag(user, 'can_manage_users')
                or user.role == UserRole.HEAD_OF_DESIGN
            )

        if permission_code == 'VIS_PERM_USER_PROFILES':
            return (
                user.role in (UserRole.ADMIN, UserRole.HEAD_OF_DESIGN)
                or PermissionService._matrix_flag(user, 'can_manage_users')
            )

        if permission_code == 'SCOPE_ALL_REQUESTS':
            return (
                PermissionService._is_admin_or_hod(user)
                or PermissionService._matrix_flag(user, 'can_view_reports')
            )

        if permission_code == 'SCOPE_OWN_REQUESTS':
            return user.role == UserRole.DESIGN_REQUESTER

        if permission_code == 'SCOPE_TEAM_REQUESTS':
            return user.role in (
                UserRole.DESIGNER,
                UserRole.VERIFICATION_TEAM,
                UserRole.COMPLIANCE_TEAM,
            ) or any(
                PermissionService._extra_flag(user, f)
                for f in ('can_verify', 'can_compliance', 'can_assign_designer')
            )

        field = ROLE_PERM_FIELDS.get(permission_code)
        if field:
            return PermissionService._matrix_flag(user, field)

        return False

    @staticmethod
    def has_project_permission(user, project, permission_code: str) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        if permission_code == 'PROJECT_PERM_VIEW':
            if PermissionService._is_admin_or_hod(user):
                return True
            return PermissionService.get_user_projects(user).filter(pk=project.pk).exists()

        if permission_code == 'PROJECT_PERM_EDIT':
            return PermissionService._is_admin_or_hod(user)

        if permission_code == 'PROJECT_PERM_COMMENT':
            return PermissionService.has_project_permission(user, project, 'PROJECT_PERM_VIEW')

        if permission_code in ('DESIGN_PERM_WORK', 'DESIGN_PERM_UPLOAD', 'DESIGN_PERM_REVISE'):
            return user.role in (UserRole.DESIGNER, UserRole.HEAD_OF_DESIGN, UserRole.ADMIN)

        if permission_code in ROLE_PERM_FIELDS:
            return PermissionService.has_global_permission(user, permission_code)

        return False

    @staticmethod
    def get_user_projects(user):
        if not user or not user.is_authenticated:
            return Project.objects.none()
        if PermissionService._is_admin_or_hod(user):
            return Project.objects.all()

        involved_project_ids = DesignRequest.objects.filter(
            Q(requested_by=user)
            | Q(assigned_designer=user)
            | Q(current_holder=user)
        ).values_list('project_id', flat=True).distinct()

        created_ids = Project.objects.filter(created_by=user).values_list('pk', flat=True)
        all_ids = set(involved_project_ids) | set(created_ids)
        return Project.objects.filter(pk__in=all_ids)

    @staticmethod
    def filter_design_requests(user, queryset=None):
        if queryset is None:
            queryset = DesignRequest.objects.all()
        if not user or not user.is_authenticated:
            return queryset.none()
        if PermissionService._is_admin_or_hod(user):
            return queryset

        if user.role == UserRole.DESIGN_REQUESTER:
            return queryset.filter(requested_by=user)

        if user.role == UserRole.DESIGNER:
            filters = Q(assigned_designer=user) | Q(current_holder=user)
            if PermissionService._extra_flag(user, 'can_verify'):
                filters |= Q(status__in=VERIFICATION_STATUSES)
            if PermissionService._extra_flag(user, 'can_compliance'):
                filters |= Q(status__in=COMPLIANCE_STATUSES)
            return queryset.filter(filters).distinct()

        if user.role == UserRole.VERIFICATION_TEAM or PermissionService._extra_flag(user, 'can_verify'):
            return queryset.filter(
                Q(status__in=VERIFICATION_STATUSES) | Q(current_holder=user)
            ).distinct()

        if user.role == UserRole.COMPLIANCE_TEAM or PermissionService._extra_flag(user, 'can_compliance'):
            return queryset.filter(
                Q(status__in=COMPLIANCE_STATUSES) | Q(current_holder=user)
            ).distinct()

        visible_project_ids = PermissionService.get_user_projects(user).values_list('pk', flat=True)
        return queryset.filter(
            Q(requested_by=user)
            | Q(assigned_designer=user)
            | Q(current_holder=user)
            | Q(project_id__in=visible_project_ids)
        ).distinct()

    @staticmethod
    def can_be_assigned_as_designer(user, project) -> bool:
        return PermissionService.has_project_permission(user, project, 'DESIGN_PERM_WORK')

    @staticmethod
    def can_verify(user, project) -> bool:
        return PermissionService.has_project_permission(user, project, 'PROJECT_PERM_VERIFY')

    @staticmethod
    def get_assignable_designers(project):
        return User.objects.filter(
            Q(role=UserRole.DESIGNER) | Q(extra_permissions__can_assign_designer=True),
            is_active=True,
            status='active',
        ).distinct()

    @staticmethod
    def get_verifiers(project):
        return User.objects.filter(
            Q(role=UserRole.VERIFICATION_TEAM) | Q(extra_permissions__can_verify=True),
            is_active=True,
            status='active',
        ).distinct()

    @staticmethod
    def get_compliance_officers(project):
        return User.objects.filter(
            Q(role=UserRole.COMPLIANCE_TEAM) | Q(extra_permissions__can_compliance=True),
            is_active=True,
            status='active',
        ).distinct()

    @staticmethod
    def can_compliance_review(user, project) -> bool:
        return PermissionService.has_project_permission(user, project, 'PROJECT_PERM_COMPLIANCE')

    @staticmethod
    def _has_my_tasks(user) -> bool:
        return user.role in (
            UserRole.ADMIN,
            UserRole.HEAD_OF_DESIGN,
            UserRole.DESIGNER,
            UserRole.VERIFICATION_TEAM,
            UserRole.COMPLIANCE_TEAM,
        )

    @staticmethod
    def get_user_sidebar_items(user) -> list:
        items = []
        if PermissionService.has_global_permission(user, 'VIS_PERM_DASHBOARD'):
            items.append('dashboard')
        items.append('projects')
        if PermissionService._can_see_design_requests(user):
            items.append('design_requests')
        if PermissionService._has_my_tasks(user):
            items.append('my_tasks')
        if PermissionService._can_see_design_library(user):
            items.append('design_library')
        if PermissionService.has_global_permission(user, 'VIS_PERM_WORKFLOW_BOARD'):
            items.append('workflow')
        if PermissionService.has_global_permission(user, 'PERM_VIEW_REPORTS'):
            items.extend(['reports', 'executive', 'leaderboard', 'workload'])
        if PermissionService.has_global_permission(user, 'VIS_PERM_TEAM_PAGE'):
            items.append('team')
        if PermissionService.has_global_permission(user, 'PERM_ADMIN_PANEL'):
            items.append('settings')
        items.extend(['profile', 'kpi', 'search'])
        if PermissionService.has_global_permission(user, 'VIS_PERM_NOTIFICATIONS'):
            items.append('notifications')
        return items

    @staticmethod
    def _can_see_design_requests(user) -> bool:
        return (
            PermissionService.has_global_permission(user, 'SCOPE_ALL_REQUESTS')
            or PermissionService.has_global_permission(user, 'SCOPE_OWN_REQUESTS')
            or PermissionService.has_global_permission(user, 'SCOPE_TEAM_REQUESTS')
            or PermissionService.get_user_projects(user).exists()
        )

    @staticmethod
    def _can_see_design_library(user) -> bool:
        return (
            PermissionService._is_admin_or_hod(user)
            or PermissionService.get_user_projects(user).exists()
        )

    @staticmethod
    def get_user_permission_labels(user) -> list:
        labels = []
        seen = set()
        perms = PermissionService._get_role_perms(user)
        if perms:
            for field, label in ROLE_PERMISSION_LABELS.items():
                if getattr(perms, field, False) and label not in seen:
                    labels.append(label)
                    seen.add(label)
        try:
            extra = user.extra_permissions
            for field, label in ROLE_PERMISSION_LABELS.items():
                if getattr(extra, field, False) and label not in seen:
                    labels.append(f'{label} (extra)')
                    seen.add(label)
        except Exception:
            pass
        return labels

    @staticmethod
    def get_user_permissions_profile(user):
        perms = PermissionService._get_role_perms(user)
        role_enabled = []
        if perms:
            for field, label in ROLE_PERMISSION_LABELS.items():
                if getattr(perms, field, False):
                    role_enabled.append({'field': field, 'label': label})
        extra_enabled = []
        try:
            extra = user.extra_permissions
            for field, label in ROLE_PERMISSION_LABELS.items():
                if getattr(extra, field, False):
                    extra_enabled.append({'field': field, 'label': label})
        except Exception:
            pass
        return {
            'role': user.role,
            'role_display': user.get_role_display(),
            'role_permissions': role_enabled,
            'extra_permissions': extra_enabled,
        }

    @staticmethod
    def get_navigation(user, request):
        """Build sidebar navigation groups from permission sidebar items."""
        if not user.is_authenticated:
            return [], [], []

        items = PermissionService.get_user_sidebar_items(user)
        dashboard_url = reverse('accounts:dashboard')

        nav_defs = {
            'dashboard': {
                'label': 'Dashboard',
                'url': dashboard_url,
                'icon': 'layout-dashboard',
                'routes': [
                    'accounts:dashboard',
                    'accounts:admin_dashboard',
                    'accounts:requester_dashboard',
                    'accounts:hod_dashboard',
                    'accounts:designer_dashboard',
                    'accounts:verification_dashboard',
                    'accounts:compliance_dashboard',
                ],
                'path_prefix': '/dashboard',
                'section': 'main',
            },
            'projects': {
                'label': 'Projects',
                'url': reverse('projects:list'),
                'icon': 'folder-kanban',
                'routes': [
                    'projects:list', 'projects:new', 'projects:detail',
                    'projects:edit', 'projects:request_new',
                ],
                'path_prefix': '/projects',
                'section': 'main',
            },
            'design_requests': {
                'label': 'Design Requests',
                'url': reverse('requests:list'),
                'icon': 'file-plus',
                'routes': ['requests:list', 'requests:detail'],
                'path_prefix': '/requests',
                'section': 'main',
            },
            'my_tasks': {
                'label': 'My Tasks',
                'url': reverse('my_tasks:list'),
                'icon': 'list-checks',
                'routes': ['my_tasks:list'],
                'path_prefix': '/my-tasks',
                'section': 'main',
            },
            'design_library': {
                'label': 'Design Library',
                'url': reverse('designs:library'),
                'icon': 'library',
                'routes': ['designs:library'],
                'path_prefix': '/designs/library',
                'section': 'main',
            },
            'workflow': {
                'label': 'Taskboard',
                'url': reverse('workflow:board'),
                'icon': 'columns-3',
                'routes': ['workflow:board', 'workflow:action', 'workflow:assign'],
                'path_prefix': '/workflow',
                'section': 'main',
            },
            'reports': {
                'label': 'Reports',
                'url': reverse('reports:index'),
                'icon': 'file-bar-chart',
                'routes': [
                    'reports:index', 'reports:export_csv',
                    'reports:export_excel', 'reports:export_pdf',
                ],
                'path_prefix': '/reports',
                'section': 'management',
            },
            'executive': {
                'label': 'Executive',
                'url': reverse('analytics:executive'),
                'icon': 'pie-chart',
                'routes': ['analytics:executive'],
                'path_prefix': '/analytics/executive',
                'section': 'management',
            },
            'leaderboard': {
                'label': 'Leaderboard',
                'url': reverse('analytics:leaderboard'),
                'icon': 'trophy',
                'routes': ['analytics:leaderboard'],
                'path_prefix': '/analytics/leaderboard',
                'section': 'management',
            },
            'workload': {
                'label': 'Workload',
                'url': reverse('analytics:workload'),
                'icon': 'users',
                'routes': ['analytics:workload'],
                'path_prefix': '/analytics/workload',
                'section': 'management',
            },
            'team': {
                'label': 'Team / Users',
                'url': reverse('accounts:user_list'),
                'icon': 'user-cog',
                'routes': [
                    'accounts:user_list', 'accounts:user_create',
                    'accounts:user_detail', 'accounts:user_edit', 'accounts:user_disable',
                ],
                'path_prefix': '/users',
                'section': 'management',
            },
            'settings': {
                'label': 'Settings',
                'url': reverse('settings:index'),
                'icon': 'settings',
                'routes': ['settings:index'],
                'path_prefix': '/settings',
                'section': 'management',
            },
            'profile': {
                'label': 'My Profile',
                'url': reverse('accounts:profile'),
                'icon': 'user',
                'routes': ['accounts:profile'],
                'path_prefix': '/profile',
                'section': 'account',
            },
            'kpi': {
                'label': 'My KPIs',
                'url': reverse('analytics:kpi'),
                'icon': 'trending-up',
                'routes': ['analytics:kpi'],
                'path_prefix': '/analytics/kpi',
                'section': 'account',
            },
            'search': {
                'label': 'Search',
                'url': reverse('analytics:search'),
                'icon': 'search',
                'routes': ['analytics:search'],
                'path_prefix': '/analytics/search',
                'section': 'account',
            },
            'notifications': {
                'label': 'Notifications',
                'url': reverse('notifications:list'),
                'icon': 'bell',
                'routes': ['notifications:list', 'notifications:mark_read', 'notifications:mark_all_read'],
                'path_prefix': '/notifications',
                'section': 'account',
            },
        }

        nav_main, nav_management, nav_account = [], [], []
        for key in items:
            item = dict(nav_defs[key])
            item['active'] = PermissionService._is_nav_active(item, request)
            section = item.pop('section')
            if section == 'main':
                nav_main.append(item)
            elif section == 'management':
                nav_management.append(item)
            else:
                nav_account.append(item)
        return nav_main, nav_management, nav_account

    @staticmethod
    def _is_nav_active(item, request):
        from django.urls import resolve

        try:
            match = resolve(request.path)
            route_key = f'{match.namespace}:{match.url_name}' if match.namespace else match.url_name
        except Exception:
            route_key = ''
        if route_key and route_key in item.get('routes', []):
            return True
        prefix = item.get('path_prefix')
        if prefix:
            prefix = prefix.rstrip('/') or '/'
            if prefix == '/':
                return request.path == '/'
            if request.path == prefix or request.path.startswith(f'{prefix}/'):
                return True
        return request.path == item['url']

    @staticmethod
    def apply_template_to_user(user, template_name, granted_by=None, projects=None):
        """Deprecated — permissions are derived from user.role only."""
        return None
