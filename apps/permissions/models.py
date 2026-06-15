from django.conf import settings
from django.db import models


class PermissionCategory(models.TextChoices):
    SYSTEM = 'system', 'System Level'
    PROJECT = 'project', 'Project Level'
    DESIGN = 'design', 'Design Execution'
    VISIBILITY = 'visibility', 'Visibility'
    SCOPE = 'scope', 'Data Scope'


class Permission(models.Model):
    """Master list of all permissions in the system."""

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=PermissionCategory.choices)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.category} → {self.name}'


class UserPermission(models.Model):
    """Global permissions assigned to a user (apply across all projects)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_permissions_custom',
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'permission')

    def __str__(self):
        return f'{self.user} — {self.permission.code}'


class ProjectMembership(models.Model):
    """Per-project permission assignment."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='members',
    )
    permissions = models.ManyToManyField(Permission, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_members',
    )
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f'{self.user} in {self.project.name}'


class RoleTemplate(models.Model):
    """Pre-built permission bundles for quick assignment."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_system_template = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
