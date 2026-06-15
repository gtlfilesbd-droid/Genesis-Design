from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    WORKFLOW = 'workflow', 'Workflow'
    SLA = 'sla', 'SLA'
    ESCALATION = 'escalation', 'Escalation'
    SYSTEM = 'system', 'System'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.WORKFLOW,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} → {self.user}'

    @property
    def is_read(self):
        return self.read_at is not None


class NotificationSetting(models.Model):
    enable_email = models.BooleanField(default=True)
    enable_in_app = models.BooleanField(default=True)
    enable_whatsapp = models.BooleanField(default=False)
    enable_sms = models.BooleanField(default=False)
    sla_warning_hours = models.PositiveSmallIntegerField(default=24)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'notification settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
