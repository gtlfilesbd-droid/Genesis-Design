from apps.accounts.models import UserRole
from apps.core.models import RolePermission

PERMISSION_FIELD_LABELS = {
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

ROLE_GROUP_ORDER = [
    UserRole.ADMIN,
    UserRole.HEAD_OF_DESIGN,
    UserRole.DESIGNER,
    UserRole.VERIFICATION_TEAM,
    UserRole.COMPLIANCE_TEAM,
    UserRole.DESIGN_REQUESTER,
]

ROLE_GROUP_DESCRIPTIONS = {
    UserRole.ADMIN: 'Full system access — all permissions enabled by default.',
    UserRole.HEAD_OF_DESIGN: 'Leads design workflow — assign, review, reports; no verify/compliance/users/settings.',
    UserRole.DESIGNER: 'Executes assigned design work only.',
    UserRole.VERIFICATION_TEAM: 'Reviews and verifies submitted designs.',
    UserRole.COMPLIANCE_TEAM: 'Performs compliance review before approval.',
    UserRole.DESIGN_REQUESTER: 'Creates projects and submits design requests.',
}


def get_role_group_permissions(role):
    """Return list of permission labels enabled for a role group."""
    try:
        rp = RolePermission.objects.get(role=role)
    except RolePermission.DoesNotExist:
        return []
    return [
        label for field, label in PERMISSION_FIELD_LABELS.items()
        if getattr(rp, field, False)
    ]


def get_role_groups_for_ui():
    """Build role group summary for user create/edit templates."""
    groups = []
    for role in ROLE_GROUP_ORDER:
        groups.append({
            'role': role,
            'label': dict(UserRole.choices).get(role, role),
            'description': ROLE_GROUP_DESCRIPTIONS.get(role, ''),
            'permissions': get_role_group_permissions(role),
        })
    return groups


def get_extra_permission_initial(user):
    """Initial checkbox values for user extra permissions form."""
    initial = {field: False for field in PERMISSION_FIELD_LABELS}
    if not user or not getattr(user, 'pk', None):
        return initial
    from apps.core.models import UserExtraPermission
    try:
        extra = user.extra_permissions
    except UserExtraPermission.DoesNotExist:
        return initial
    for field in PERMISSION_FIELD_LABELS:
        initial[field] = getattr(extra, field, False)
    return initial


def save_user_extra_permissions(user, post_data, prefix='extra_'):
    from apps.core.models import UserExtraPermission

    extra, _ = UserExtraPermission.objects.get_or_create(user=user)
    for field in PERMISSION_FIELD_LABELS:
        setattr(extra, field, post_data.get(f'{prefix}{field}') == 'on')
    extra.save()
    return extra
