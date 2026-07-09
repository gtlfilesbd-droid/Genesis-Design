from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User, UserRole
from apps.core.models import UserExtraPermission
from apps.core.settings_forms import ensure_role_permissions


ROLE_TO_GROUP = {
    UserRole.ADMIN: "Admin",
    UserRole.HEAD_OF_DESIGN: "Head of Design",
    UserRole.DESIGNER: "Designer",
    UserRole.VERIFICATION_TEAM: "Verification Team",
    UserRole.COMPLIANCE_TEAM: "Compliance Team",
    UserRole.DESIGN_REQUESTER: "Design Requester",
}

MANAGED_GROUP_NAMES = set(ROLE_TO_GROUP.values())


def _perm(app_label: str, model: str, action: str):
    try:
        ct = ContentType.objects.get(app_label=app_label, model=model)
    except ContentType.DoesNotExist:
        return None
    codename = f"{action}_{model}"
    return Permission.objects.filter(content_type=ct, codename=codename).first()


def _model_perms(app_label: str, model: str, actions):
    perms = []
    for action in actions:
        p = _perm(app_label, model, action)
        if p:
            perms.append(p)
    return perms


def _extra_to_auth_perms(extra: UserExtraPermission):
    """
    Map UserExtraPermission -> Django auth.Permission list.
    This is purely for Django Admin visibility on the User change page.
    """
    perms = []

    # Always safe view perms for inspection
    perms += _model_perms("projects", "project", ["view"])
    perms += _model_perms("designs", "designrequest", ["view"])

    if extra.can_create_project:
        perms += _model_perms("projects", "project", ["add", "change", "view"])
        perms += _model_perms("projects", "projectattachment", ["add", "change", "delete", "view"])

    if extra.can_edit_project or extra.can_add_project_team:
        perms += _model_perms("projects", "project", ["change", "view"])

    if extra.can_create_request:
        perms += _model_perms("designs", "designrequest", ["add", "view"])

    if extra.can_assign_designer or extra.can_review or extra.can_verify or extra.can_compliance:
        perms += _model_perms("designs", "designrequest", ["change", "view"])

    if extra.can_verify:
        perms += _model_perms("designs", "verification", ["add", "change", "view"])

    if extra.can_compliance:
        perms += _model_perms("designs", "compliancereview", ["add", "change", "view"])

    if extra.can_manage_users:
        perms += _model_perms("accounts", "user", ["add", "change", "delete", "view"])
        perms += _model_perms("accounts", "team", ["add", "change", "delete", "view"])
        perms += _model_perms("core", "userextrapermission", ["add", "change", "delete", "view"])

    if extra.can_manage_settings:
        perms += _model_perms("core", "companysettings", ["change", "view"])
        perms += _model_perms("core", "deadlineconfiguration", ["change", "view"])
        perms += _model_perms("core", "rolepermission", ["change", "view"])
        perms += _model_perms("notifications", "notificationsetting", ["change", "view"])
        perms += _model_perms("designs", "drawingtype", ["add", "change", "delete", "view"])

    # De-dup
    seen = set()
    unique = []
    for p in perms:
        if p.pk not in seen:
            unique.append(p)
            seen.add(p.pk)
    return unique


def sync_user_group_and_permissions(user: User):
    """
    Ensure user is in exactly one managed role group based on user.role.
    Also mirror UserExtraPermission into user.user_permissions for admin visibility.
    """
    if not user or not user.pk:
        return

    ensure_role_permissions()

    desired = ROLE_TO_GROUP.get(user.role)
    if desired:
        # remove other managed groups, keep any unrelated groups untouched
        managed_groups = Group.objects.filter(name__in=MANAGED_GROUP_NAMES)
        user.groups.remove(*managed_groups.exclude(name=desired))
        group, _ = Group.objects.get_or_create(name=desired)
        user.groups.add(group)

    # Sync extra -> auth user_permissions (best-effort)
    try:
        extra = user.extra_permissions
    except UserExtraPermission.DoesNotExist:
        extra = None

    if extra:
        perms_to_add = _extra_to_auth_perms(extra)
        # Remove existing perms for our content types to avoid stale leftovers, keep other app perms
        managed_app_labels = {"projects", "designs", "accounts", "core", "notifications"}
        managed_cts = ContentType.objects.filter(app_label__in=managed_app_labels)
        user.user_permissions.remove(*Permission.objects.filter(content_type__in=managed_cts))
        user.user_permissions.add(*perms_to_add)
    else:
        # If no extra perms, clear managed app user_permissions so page doesn't mislead
        managed_app_labels = {"projects", "designs", "accounts", "core", "notifications"}
        managed_cts = ContentType.objects.filter(app_label__in=managed_app_labels)
        user.user_permissions.remove(*Permission.objects.filter(content_type__in=managed_cts))


@receiver(post_save, sender=User)
def _on_user_saved(sender, instance: User, created, **kwargs):
    sync_user_group_and_permissions(instance)

