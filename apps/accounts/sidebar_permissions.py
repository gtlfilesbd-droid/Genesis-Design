from apps.accounts.models import UserRole
from apps.core.models import UserSidebarPermission

SIDEBAR_ITEMS = [
    {'key': 'dashboard', 'field': 'nav_dashboard', 'label': 'Dashboard', 'permission_code': 'NAV_PERM_DASHBOARD'},
    {'key': 'projects', 'field': 'nav_projects', 'label': 'Projects', 'permission_code': 'NAV_PERM_PROJECTS'},
    {'key': 'my_tasks', 'field': 'nav_my_tasks', 'label': 'My Tasks', 'permission_code': 'NAV_PERM_MY_TASKS'},
    {'key': 'design_library', 'field': 'nav_design_library', 'label': 'Design Library', 'permission_code': 'NAV_PERM_DESIGN_LIBRARY'},
    {'key': 'workflow', 'field': 'nav_taskboard', 'label': 'Taskboard', 'permission_code': 'NAV_PERM_TASKBOARD'},
    {'key': 'reports', 'field': 'nav_reports', 'label': 'Reports', 'permission_code': 'NAV_PERM_REPORTS'},
    {'key': 'executive', 'field': 'nav_executive', 'label': 'Executive', 'permission_code': 'NAV_PERM_EXECUTIVE'},
    {'key': 'leaderboard', 'field': 'nav_leaderboard', 'label': 'Leaderboard', 'permission_code': 'NAV_PERM_LEADERBOARD'},
    {'key': 'workload', 'field': 'nav_workload', 'label': 'Workload', 'permission_code': 'NAV_PERM_WORKLOAD'},
    {'key': 'team', 'field': 'nav_team', 'label': 'Team / Users', 'permission_code': 'NAV_PERM_TEAM'},
    {'key': 'settings', 'field': 'nav_settings', 'label': 'Settings', 'permission_code': 'NAV_PERM_SETTINGS'},
    {'key': 'profile', 'field': 'nav_profile', 'label': 'My Profile', 'permission_code': 'NAV_PERM_PROFILE'},
    {'key': 'kpi', 'field': 'nav_kpi', 'label': 'My KPIs', 'permission_code': 'NAV_PERM_KPI'},
    {'key': 'notifications', 'field': 'nav_notifications', 'label': 'Notifications', 'permission_code': 'NAV_PERM_NOTIFICATIONS'},
]

SIDEBAR_FIELD_NAMES = [item['field'] for item in SIDEBAR_ITEMS]

NAV_PERM_FIELDS = {item['permission_code']: item['field'] for item in SIDEBAR_ITEMS}

LEGACY_NAV_PERM_MAP = {
    'VIS_PERM_DASHBOARD': 'nav_dashboard',
    'VIS_PERM_NOTIFICATIONS': 'nav_notifications',
    'VIS_PERM_WORKFLOW_BOARD': 'nav_taskboard',
    'VIS_PERM_TEAM_PAGE': 'nav_team',
}

_ALL_TRUE = {field: True for field in SIDEBAR_FIELD_NAMES}

DEFAULT_SIDEBAR_BY_ROLE = {
    UserRole.ADMIN: dict(_ALL_TRUE),
    UserRole.HEAD_OF_DESIGN: {
        'nav_dashboard': True,
        'nav_projects': True,
        'nav_my_tasks': True,
        'nav_design_library': True,
        'nav_taskboard': True,
        'nav_reports': True,
        'nav_executive': True,
        'nav_leaderboard': True,
        'nav_workload': True,
        'nav_team': False,
        'nav_settings': False,
        'nav_profile': True,
        'nav_kpi': True,
        'nav_notifications': True,
    },
    UserRole.DESIGNER: {
        'nav_dashboard': True,
        'nav_projects': True,
        'nav_my_tasks': True,
        'nav_design_library': True,
        'nav_taskboard': False,
        'nav_reports': False,
        'nav_executive': False,
        'nav_leaderboard': False,
        'nav_workload': False,
        'nav_team': False,
        'nav_settings': False,
        'nav_profile': True,
        'nav_kpi': True,
        'nav_notifications': True,
    },
    UserRole.VERIFICATION_TEAM: {
        'nav_dashboard': True,
        'nav_projects': True,
        'nav_my_tasks': True,
        'nav_design_library': True,
        'nav_taskboard': False,
        'nav_reports': False,
        'nav_executive': False,
        'nav_leaderboard': False,
        'nav_workload': False,
        'nav_team': False,
        'nav_settings': False,
        'nav_profile': True,
        'nav_kpi': True,
        'nav_notifications': True,
    },
    UserRole.COMPLIANCE_TEAM: {
        'nav_dashboard': True,
        'nav_projects': True,
        'nav_my_tasks': True,
        'nav_design_library': True,
        'nav_taskboard': False,
        'nav_reports': False,
        'nav_executive': False,
        'nav_leaderboard': False,
        'nav_workload': False,
        'nav_team': False,
        'nav_settings': False,
        'nav_profile': True,
        'nav_kpi': True,
        'nav_notifications': True,
    },
    UserRole.DESIGN_REQUESTER: {
        'nav_dashboard': True,
        'nav_projects': True,
        'nav_my_tasks': True,
        'nav_design_library': True,
        'nav_taskboard': False,
        'nav_reports': False,
        'nav_executive': False,
        'nav_leaderboard': False,
        'nav_workload': False,
        'nav_team': False,
        'nav_settings': False,
        'nav_profile': True,
        'nav_kpi': True,
        'nav_notifications': True,
    },
}


def get_default_sidebar_for_role(role):
    defaults = DEFAULT_SIDEBAR_BY_ROLE.get(role, {})
    return {field: defaults.get(field, False) for field in SIDEBAR_FIELD_NAMES}


def get_sidebar_permission_initial(user=None, role=None):
    """Checkbox state for user create/edit forms."""
    if user and getattr(user, 'pk', None):
        try:
            sidebar = user.sidebar_permissions
            return {field: getattr(sidebar, field, False) for field in SIDEBAR_FIELD_NAMES}
        except UserSidebarPermission.DoesNotExist:
            pass
    effective_role = role or (user.role if user else UserRole.DESIGN_REQUESTER)
    return get_default_sidebar_for_role(effective_role)


def save_user_sidebar_permissions(user, post_data, prefix='nav_'):
    defaults = get_default_sidebar_for_role(user.role)
    sidebar, _ = UserSidebarPermission.objects.get_or_create(user=user, defaults=defaults)
    for field in SIDEBAR_FIELD_NAMES:
        setattr(sidebar, field, post_data.get(f'{prefix}{field}') == 'on')
    sidebar.save()
    if hasattr(user, '_cached_sidebar_perms'):
        delattr(user, '_cached_sidebar_perms')
    return sidebar


def get_sidebar_defaults_for_ui():
    """Role -> field defaults for JS pre-fill on user form."""
    return {
        role: get_default_sidebar_for_role(role)
        for role in DEFAULT_SIDEBAR_BY_ROLE
    }
