from django.db.models import Q
from django.urls import reverse

from apps.accounts.models import User
from apps.designs.models import DesignRequest, DesignStatus
from apps.projects.models import Project

from .models import Permission, ProjectMembership, UserPermission

GLOBAL_PROJECT_CODES = frozenset({'PROJECT_PERM_CREATE'})


class PermissionService:
    """Central service for all permission checks."""

    @staticmethod
    def has_global_permission(user, permission_code: str) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return UserPermission.objects.filter(
            user=user,
            permission__code=permission_code,
            is_active=True,
        ).exists()

    @staticmethod
    def has_project_permission(user, project, permission_code: str) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if PermissionService.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'):
            if permission_code == 'PROJECT_PERM_VIEW':
                return True
        if permission_code in GLOBAL_PROJECT_CODES:
            return PermissionService.has_global_permission(user, permission_code)
        try:
            membership = ProjectMembership.objects.get(
                user=user,
                project=project,
                is_active=True,
            )
            return membership.permissions.filter(code=permission_code).exists()
        except ProjectMembership.DoesNotExist:
            return False

    @staticmethod
    def get_user_projects(user):
        if not user or not user.is_authenticated:
            return Project.objects.none()
        if user.is_superuser or PermissionService.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS'):
            return Project.objects.all()
        return Project.objects.filter(
            members__user=user,
            members__is_active=True,
            members__permissions__code='PROJECT_PERM_VIEW',
        ).distinct()

    @staticmethod
    def filter_design_requests(user, queryset=None):
        if queryset is None:
            queryset = DesignRequest.objects.all()
        if not user or not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or PermissionService.has_global_permission(user, 'SCOPE_ALL_REQUESTS'):
            return queryset
        if PermissionService.has_global_permission(user, 'SCOPE_TEAM_REQUESTS'):
            team_user_ids = User.objects.filter(
                Q(team=user.team) | Q(manager=user) | Q(pk=user.pk)
            ).values_list('pk', flat=True)
            return queryset.filter(
                Q(requested_by_id__in=team_user_ids)
                | Q(assigned_designer_id__in=team_user_ids)
                | Q(current_holder_id__in=team_user_ids)
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
            project_memberships__project=project,
            project_memberships__is_active=True,
            project_memberships__permissions__code='DESIGN_PERM_WORK',
            is_active=True,
        ).distinct()

    @staticmethod
    def get_verifiers(project):
        return User.objects.filter(
            project_memberships__project=project,
            project_memberships__is_active=True,
            project_memberships__permissions__code='PROJECT_PERM_VERIFY',
            is_active=True,
        ).distinct()

    @staticmethod
    def get_user_sidebar_items(user) -> list:
        items = []
        if PermissionService.has_global_permission(user, 'VIS_PERM_DASHBOARD'):
            items.append('dashboard')
        items.append('projects')
        if PermissionService._can_see_design_requests(user):
            items.append('design_requests')
        has_tasks = ProjectMembership.objects.filter(
            user=user,
            is_active=True,
            permissions__code__in=[
                'DESIGN_PERM_WORK',
                'PROJECT_PERM_ASSIGN',
                'PROJECT_PERM_VERIFY',
            ],
        ).exists()
        if has_tasks:
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
        if PermissionService.has_global_permission(user, 'SCOPE_ALL_REQUESTS'):
            return True
        if PermissionService.has_global_permission(user, 'SCOPE_OWN_REQUESTS'):
            return True
        if PermissionService.has_global_permission(user, 'SCOPE_TEAM_REQUESTS'):
            return True
        return ProjectMembership.objects.filter(
            user=user,
            is_active=True,
            permissions__code='PROJECT_PERM_VIEW',
        ).exists()

    @staticmethod
    def _can_see_design_library(user) -> bool:
        return (
            PermissionService.has_global_permission(user, 'PERM_VIEW_ALL_PROJECTS')
            or ProjectMembership.objects.filter(
                user=user,
                is_active=True,
                permissions__code='PROJECT_PERM_VIEW',
            ).exists()
        )

    @staticmethod
    def get_user_permission_labels(user) -> list:
        detail = PermissionService.get_user_permissions_profile(user)
        labels = [p.name for p in detail['global_permissions']]
        for membership in detail['project_memberships']:
            for perm in membership.permissions.all():
                if perm.name not in labels:
                    labels.append(perm.name)
        return labels[:12]

    @staticmethod
    def get_user_permissions_profile(user):
        """Full permission breakdown for profile page."""
        global_permissions = list(
            Permission.objects.filter(
                userpermission__user=user,
                userpermission__is_active=True,
            ).order_by('category', 'name')
        )
        project_memberships = list(
            ProjectMembership.objects.filter(
                user=user,
                is_active=True,
            ).select_related('project').prefetch_related('permissions').order_by('project__code')
        )
        return {
            'global_permissions': global_permissions,
            'project_memberships': project_memberships,
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
        """Apply a role template — global perms to UserPermission, project perms to memberships."""
        from .models import RoleTemplate

        template = RoleTemplate.objects.get(name=template_name)
        if projects is None:
            projects = Project.objects.all()

        global_categories = {'system', 'visibility', 'scope'}
        global_codes = GLOBAL_PROJECT_CODES

        for perm in template.permissions.all():
            if perm.category in global_categories or perm.code in global_codes:
                UserPermission.objects.update_or_create(
                    user=user,
                    permission=perm,
                    defaults={'granted_by': granted_by, 'is_active': True},
                )

        project_perms = template.permissions.exclude(
            category__in=global_categories,
        ).exclude(code__in=global_codes)

        for project in projects:
            membership, _ = ProjectMembership.objects.get_or_create(
                user=user,
                project=project,
                defaults={'added_by': granted_by, 'is_active': True},
            )
            membership.is_active = True
            membership.save(update_fields=['is_active'])
            membership.permissions.add(*project_perms)
