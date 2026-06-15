from django.urls import reverse, resolve


def genesis_navigation(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user
    nav_main = [
        {'label': 'Dashboard', 'url': reverse(user.get_dashboard_url_name()), 'icon': 'layout-dashboard',
         'names': ['admin_dashboard', 'requester_dashboard', 'hod_dashboard', 'designer_dashboard', 'verification_dashboard', 'dashboard']},
        {'label': 'Projects', 'url': reverse('projects:list'), 'icon': 'folder-kanban', 'names': ['list', 'new', 'detail', 'edit', 'request_new']},
        {'label': 'Design Requests', 'url': reverse('requests:list'), 'icon': 'file-plus', 'names': ['list', 'detail']},
        {'label': 'My Tasks', 'url': reverse('my_tasks:list'), 'icon': 'list-checks', 'names': ['list']},
        {'label': 'Design Library', 'url': reverse('designs:library'), 'icon': 'library', 'names': ['library']},
        {'label': 'Taskboard', 'url': reverse('workflow:board'), 'icon': 'columns-3', 'names': ['board']},
    ]

    nav_management = []
    if user.is_genesis_admin or user.is_head_of_design:
        nav_management.extend([
            {'label': 'Reports', 'url': reverse('reports:index'), 'icon': 'file-bar-chart', 'names': ['index', 'export_csv', 'export_excel', 'export_pdf']},
            {'label': 'Executive', 'url': reverse('analytics:executive'), 'icon': 'pie-chart', 'names': ['executive']},
            {'label': 'Leaderboard', 'url': reverse('analytics:leaderboard'), 'icon': 'trophy', 'names': ['leaderboard']},
            {'label': 'Workload', 'url': reverse('analytics:workload'), 'icon': 'users', 'names': ['workload']},
        ])
    if user.is_genesis_admin:
        nav_management.extend([
            {'label': 'Team / Users', 'url': reverse('accounts:user_list'), 'icon': 'user-cog',
             'names': ['user_list', 'user_create', 'user_detail', 'user_edit', 'user_disable']},
            {'label': 'Settings', 'url': reverse('settings:index'), 'icon': 'settings', 'names': ['index']},
        ])

    nav_account = [
        {'label': 'My Profile', 'url': reverse('accounts:profile'), 'icon': 'user', 'names': ['profile']},
        {'label': 'My KPIs', 'url': reverse('analytics:kpi'), 'icon': 'trending-up', 'names': ['kpi']},
        {'label': 'Search', 'url': reverse('analytics:search'), 'icon': 'search', 'names': ['search']},
        {'label': 'Notifications', 'url': reverse('notifications:list'), 'icon': 'bell', 'names': ['list', 'mark_read', 'mark_all_read']},
    ]

    current_name = ''
    try:
        match = resolve(request.path)
        current_name = match.url_name or ''
        current_namespace = match.namespace
    except Exception:
        current_namespace = ''

    def is_active(item):
        if item['names'] and current_name in item['names']:
            if current_namespace in ('projects', 'designs', 'workflow', 'reports', 'analytics',
                                     'notifications', 'accounts', 'requests', 'my_tasks', 'settings'):
                return True
        if request.path == item['url']:
            return True
        if item['url'] != '/' and request.path.startswith(item['url'].rstrip('/')):
            return True
        return False

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
