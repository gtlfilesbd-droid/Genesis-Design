from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.accounts.models import UserRole
from apps.core.models import RolePermission
from apps.core.settings_forms import ensure_role_permissions


def _perm(app_label: str, model: str, action: str):
    """
    Return a Django auth Permission like add/change/delete/view for a model.
    If a model permission does not exist, return None (safe for optional models).
    """
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


ROLE_GROUPS = [
    (UserRole.ADMIN, "Admin"),
    (UserRole.HEAD_OF_DESIGN, "Head of Design"),
    (UserRole.DESIGNER, "Designer"),
    (UserRole.VERIFICATION_TEAM, "Verification Team"),
    (UserRole.COMPLIANCE_TEAM, "Compliance Team"),
    (UserRole.DESIGN_REQUESTER, "Design Requester"),
]


class Command(BaseCommand):
    help = "Sync Django auth Groups for the 6 role groups"

    def handle(self, *args, **options):
        ensure_role_permissions()

        # Base permissions by capability
        # Note: This is for Django Admin convenience only. Runtime enforcement is role-based.
        for role, group_name in ROLE_GROUPS:
            rp = RolePermission.objects.filter(role=role).first()
            if not rp:
                self.stdout.write(self.style.WARNING(f"Skipping {group_name}: RolePermission row missing"))
                continue

            perms = []

            # Always allow viewing core operational data needed for admin inspection.
            perms += _model_perms("projects", "project", ["view"])
            perms += _model_perms("designs", "designrequest", ["view"])
            perms += _model_perms("designs", "drawingtype", ["view"])

            # Projects
            if rp.can_create_project:
                perms += _model_perms("projects", "project", ["add", "change", "view"])
                perms += _model_perms("projects", "projectattachment", ["add", "change", "delete", "view"])

            # Requests
            if rp.can_create_request:
                perms += _model_perms("designs", "designrequest", ["add", "view"])

            # Workflow management (assign/review/verify/compliance) requires editing requests
            if rp.can_assign_designer or rp.can_review or rp.can_verify or rp.can_compliance:
                perms += _model_perms("designs", "designrequest", ["change", "view"])

            # Verification/compliance artifacts (optional)
            if rp.can_verify:
                perms += _model_perms("designs", "verification", ["add", "change", "view"])
            if rp.can_compliance:
                perms += _model_perms("designs", "compliancereview", ["add", "change", "view"])

            # File uploads / attachments
            perms += _model_perms("designs", "requestattachment", ["add", "change", "delete", "view"])

            # Users
            if rp.can_manage_users:
                perms += _model_perms("accounts", "user", ["add", "change", "delete", "view"])
                perms += _model_perms("accounts", "team", ["add", "change", "delete", "view"])
                perms += _model_perms("core", "userextrapermission", ["add", "change", "delete", "view"])

            # Reports: no specific DB model perms; allow viewing core data
            if rp.can_view_reports:
                perms += _model_perms("designs", "designrequest", ["view"])
                perms += _model_perms("projects", "project", ["view"])

            # Settings / configuration
            if rp.can_manage_settings:
                perms += _model_perms("core", "companysettings", ["change", "view"])
                perms += _model_perms("core", "deadlineconfiguration", ["change", "view"])
                perms += _model_perms("core", "rolepermission", ["change", "view"])
                perms += _model_perms("notifications", "notificationsetting", ["change", "view"])
                perms += _model_perms("designs", "drawingtype", ["add", "change", "delete", "view"])

            # De-duplicate
            unique = []
            seen = set()
            for p in perms:
                if p.pk not in seen:
                    unique.append(p)
                    seen.add(p.pk)

            group, _ = Group.objects.get_or_create(name=group_name)
            group.permissions.set(unique)

            self.stdout.write(self.style.SUCCESS(f"Synced Group: {group_name} ({len(unique)} permissions)"))

