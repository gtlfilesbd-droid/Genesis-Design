from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    DESIGN_REQUESTER = 'design_requester', 'Design Requester'
    HEAD_OF_DESIGN = 'head_of_design', 'Head of Design'
    DESIGNER = 'designer', 'Designer'
    VERIFICATION_TEAM = 'verification_team', 'Verification Team'
    COMPLIANCE_TEAM = 'compliance_team', 'Compliance Team'
    ADMIN = 'admin', 'Admin'


class UserStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'


class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.DESIGN_REQUESTER,
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
    )
    mobile_number = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_design_requester(self):
        return self.role == UserRole.DESIGN_REQUESTER

    @property
    def is_head_of_design(self):
        return self.role == UserRole.HEAD_OF_DESIGN

    @property
    def is_designer(self):
        return self.role == UserRole.DESIGNER

    @property
    def is_verification_team(self):
        return self.role == UserRole.VERIFICATION_TEAM

    @property
    def is_compliance_team(self):
        return self.role == UserRole.COMPLIANCE_TEAM

    @property
    def is_genesis_admin(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    def get_dashboard_url_name(self):
        return {
            UserRole.ADMIN: 'accounts:admin_dashboard',
            UserRole.DESIGN_REQUESTER: 'accounts:requester_dashboard',
            UserRole.HEAD_OF_DESIGN: 'accounts:hod_dashboard',
            UserRole.DESIGNER: 'accounts:designer_dashboard',
            UserRole.VERIFICATION_TEAM: 'accounts:verification_dashboard',
            UserRole.COMPLIANCE_TEAM: 'accounts:compliance_dashboard',
        }.get(self.role, 'accounts:dashboard')
