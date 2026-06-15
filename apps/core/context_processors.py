from django.urls import reverse, resolve


def _route_key(namespace, url_name):
    if namespace:
        return f'{namespace}:{url_name}'
    return url_name or ''


def _path_under(prefix, path):
    prefix = prefix.rstrip('/') or '/'
    if prefix == '/':
        return path == '/'
    return path == prefix or path.startswith(f'{prefix}/')


def genesis_navigation(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    nav_main = [
        {
            'label': 'Dashboard',
            'url': reverse(user.get_dashboard_url_name()),
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
        },
        {
            'label': 'Projects',
            'url': reverse('projects:list'),
            'icon': 'folder-kanban',
            'routes': ['projects:list', 'projects:new', 'projects:detail', 'projects:edit', 'projects:request_new'],
            'path_prefix': '/projects',
        },
        {
            'label': 'Design Requests',
            'url': reverse('requests:list'),
            'icon': 'file-plus',
            'routes': ['requests:list', 'requests:detail'],
            'path_prefix': '/requests',
        },
        {
            'label': 'My Tasks',
            'url': reverse('my_tasks:list'),
            'icon': 'list-checks',
            'routes': ['my_tasks:list'],
            'path_prefix': '/my-tasks',
        },
        {
            'label': 'Design Library',
            'url': reverse('designs:library'),
            'icon': 'library',
            'routes': ['designs:library'],
            'path_prefix': '/designs/library',
        },
        {
            'label': 'Taskboard',
            'url': reverse('workflow:board'),
            'icon': 'columns-3',
            'routes': ['workflow:board', 'workflow:action', 'workflow:assign'],
            'path_prefix': '/workflow',
        },
    ]

    nav_management = []
    if user.is_genesis_admin or user.is_head_of_design:
        nav_management.extend([
            {
                'label': 'Reports',
                'url': reverse('reports:index'),
                'icon': 'file-bar-chart',
                'routes': ['reports:index', 'reports:export_csv', 'reports:export_excel', 'reports:export_pdf'],
                'path_prefix': '/reports',
            },
            {
                'label': 'Executive',
                'url': reverse('analytics:executive'),
                'icon': 'pie-chart',
                'routes': ['analytics:executive'],
                'path_prefix': '/analytics/executive',
            },
            {
                'label': 'Leaderboard',
                'url': reverse('analytics:leaderboard'),
                'icon': 'trophy',
                'routes': ['analytics:leaderboard'],
                'path_prefix': '/analytics/leaderboard',
            },
            {
                'label': 'Workload',
                'url': reverse('analytics:workload'),
                'icon': 'users',
                'routes': ['analytics:workload'],
                'path_prefix': '/analytics/workload',
            },
        ])
    if user.is_genesis_admin:
        nav_management.extend([
            {
                'label': 'Team / Users',
                'url': reverse('accounts:user_list'),
                'icon': 'user-cog',
                'routes': [
                    'accounts:user_list',
                    'accounts:user_create',
                    'accounts:user_detail',
                    'accounts:user_edit',
                    'accounts:user_disable',
                ],
                'path_prefix': '/users',
            },
            {
                'label': 'Settings',
                'url': reverse('settings:index'),
                'icon': 'settings',
                'routes': ['settings:index'],
                'path_prefix': '/settings',
            },
        ])

    nav_account = [
        {
            'label': 'My Profile',
            'url': reverse('accounts:profile'),
            'icon': 'user',
            'routes': ['accounts:profile'],
            'path_prefix': '/profile',
        },
        {
            'label': 'My KPIs',
            'url': reverse('analytics:kpi'),
            'icon': 'trending-up',
            'routes': ['analytics:kpi'],
            'path_prefix': '/analytics/kpi',
        },
        {
            'label': 'Search',
            'url': reverse('analytics:search'),
            'icon': 'search',
            'routes': ['analytics:search'],
            'path_prefix': '/analytics/search',
        },
        {
            'label': 'Notifications',
            'url': reverse('notifications:list'),
            'icon': 'bell',
            'routes': ['notifications:list', 'notifications:mark_read', 'notifications:mark_all_read'],
            'path_prefix': '/notifications',
        },
    ]

    try:
        match = resolve(request.path)
        current_route = _route_key(match.namespace, match.url_name)
    except Exception:
        current_route = ''

    def is_active(item):
        if current_route and current_route in item.get('routes', []):
            return True
        path_prefix = item.get('path_prefix')
        if path_prefix and _path_under(path_prefix, request.path):
            return True
        return request.path == item['url']

    for group in (nav_main, nav_management, nav_account):
        for item in group:
            item['active'] = is_active(item)

    breadcrumbs = _build_breadcrumbs(request)

    return {
        'nav_main': nav_main,
        'nav_management': nav_management,
        'nav_account': nav_account,
        'breadcrumbs': breadcrumbs,
    }


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
    elif parts[0] == 'workflow':
        crumbs.append({'label': 'Workflow Board', 'url': None})
    elif parts[0] == 'reports':
        crumbs.append({'label': 'Reports', 'url': None})

    return crumbs
