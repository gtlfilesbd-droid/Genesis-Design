from django.conf import settings
from django.db import models


class ProjectStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    ON_HOLD = 'on_hold', 'On Hold'


class Project(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    client_name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    start_date = models.DateField()
    expected_completion_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    health_score = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} - {self.name}'

    @property
    def total_design_requests(self):
        return self.design_requests.count()

    @property
    def running_designs(self):
        from apps.designs.models import DesignStatus
        terminal = [DesignStatus.COMPLETED, DesignStatus.CANCELLED]
        return self.design_requests.exclude(status__in=terminal).count()

    @property
    def completed_designs(self):
        from apps.designs.models import DesignStatus
        return self.design_requests.filter(status=DesignStatus.COMPLETED).count()


class ProjectAttachment(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(upload_to='project_attachments/%Y/%m/')
    name = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.file.name
