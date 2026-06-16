from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f'{self.action} by {self.user} at {self.created_at}'


class AuditEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_entries',
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device = models.CharField(max_length=255, blank=True)
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'audit entries'

    def __str__(self):
        return f'{self.action} - {self.user} - {self.created_at}'


class StageDuration(models.Model):
    """Tracks time spent in each workflow stage for delay analysis."""
    design = models.ForeignKey(
        'designs.DesignRequest',
        on_delete=models.CASCADE,
        related_name='stage_durations',
    )
    stage = models.CharField(max_length=50)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['started_at']

    @property
    def duration_days(self):
        if not self.ended_at:
            return None
        delta = self.ended_at - self.started_at
        return delta.total_seconds() / 86400


class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200, default='Genesis Design')
    tagline = models.CharField(max_length=255, default='Design Management System')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True, default='info@genesisdesign.local')
    website = models.URLField(blank=True)
    timezone_name = models.CharField(max_length=64, default='Asia/Dhaka')
    file_sharing_policy = models.TextField(
        blank=True,
        default=(
            'Design files must be stored on the company internal file sharing system '
            '(shared drive, BIM server, or CAD server). Genesis Design stores references only.'
        ),
        help_text='Shown on submit forms and design detail pages.',
    )

    class Meta:
        verbose_name_plural = 'company settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DeadlineConfiguration(models.Model):
    default_warning_percent = models.PositiveSmallIntegerField(
        default=20,
        help_text='Show warning when this percent of the allowed time remains.',
    )
    escalation_level_1_days = models.PositiveSmallIntegerField(default=1)
    escalation_level_1_hours = models.PositiveSmallIntegerField(default=0)
    escalation_level_2_days = models.PositiveSmallIntegerField(default=3)
    escalation_level_2_hours = models.PositiveSmallIntegerField(default=0)
    escalation_level_3_days = models.PositiveSmallIntegerField(default=4)
    escalation_level_3_hours = models.PositiveSmallIntegerField(default=0)
    escalation_level_4_days = models.PositiveSmallIntegerField(default=5)
    escalation_level_4_hours = models.PositiveSmallIntegerField(default=0)
    auto_breach_notify = models.BooleanField(
        default=True,
        help_text='Send a notification when a design first misses its deadline.',
    )
    count_weekends = models.BooleanField(
        default=False,
        help_text='Count only weekdays when calculating deadline due dates.',
    )

    class Meta:
        verbose_name_plural = 'Deadline configuration'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RolePermission(models.Model):
    role = models.CharField(max_length=30, unique=True)
    can_create_project = models.BooleanField(default=False)
    can_create_request = models.BooleanField(default=False)
    can_assign_designer = models.BooleanField(default=False)
    can_review = models.BooleanField(default=False)
    can_verify = models.BooleanField(default=False)
    can_compliance = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'role permissions'

    def __str__(self):
        return self.role


class UserExtraPermission(models.Model):
    """Optional extra permissions for a user beyond their role group."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='extra_permissions',
    )
    can_create_project = models.BooleanField(default=False)
    can_create_request = models.BooleanField(default=False)
    can_assign_designer = models.BooleanField(default=False)
    can_review = models.BooleanField(default=False)
    can_verify = models.BooleanField(default=False)
    can_compliance = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'user extra permissions'

    def __str__(self):
        return f'Extra permissions for {self.user}'

    def enabled_labels(self):
        from apps.accounts.role_groups import PERMISSION_FIELD_LABELS
        return [
            PERMISSION_FIELD_LABELS[field]
            for field in PERMISSION_FIELD_LABELS
            if getattr(self, field, False)
        ]
