from django.utils import timezone


PROJECT_AUDIT_FIELDS = (
    'client_name', 'code', 'address',
    'project_director_id', 'project_engineer_id',
    'project_coordinator_id', 'project_manager_id',
    'start_date', 'expected_completion_date', 'description', 'status',
)


def project_user_display(user):
    if not user:
        return 'System'
    return user.get_full_name() or user.username


def format_project_timestamp(dt):
    if not dt:
        return '—'
    return timezone.localtime(dt).strftime('%d %b %Y, %I:%M %p')


def _fk_display(obj):
    if not obj:
        return None
    return str(obj)


def project_audit_snapshot(project):
    return {
        'client_name': project.client_name,
        'code': project.code,
        'address': project.address,
        'project_director_id': project.project_director_id,
        'project_director': _fk_display(project.project_director),
        'project_engineer_id': project.project_engineer_id,
        'project_engineer': _fk_display(project.project_engineer),
        'project_coordinator_id': project.project_coordinator_id,
        'project_coordinator': project_user_display(project.project_coordinator),
        'project_manager_id': project.project_manager_id,
        'project_manager': project_user_display(project.project_manager),
        'start_date': project.start_date.isoformat() if project.start_date else None,
        'expected_completion_date': (
            project.expected_completion_date.isoformat()
            if project.expected_completion_date else None
        ),
        'description': project.description,
        'status': project.status,
    }


def project_changed_fields(before, after):
    labels = {
        'client_name': 'Client name',
        'code': 'Short name',
        'address': 'Address',
        'project_director_id': 'Project director',
        'project_engineer_id': 'Project engineer',
        'project_coordinator_id': 'Project coordinator',
        'project_manager_id': 'Project manager',
        'start_date': 'Start date',
        'expected_completion_date': 'Target completion',
        'description': 'Description',
        'status': 'Status',
    }
    changed = []
    for key in PROJECT_AUDIT_FIELDS:
        if before.get(key) != after.get(key):
            changed.append(labels.get(key, key))
    return changed
