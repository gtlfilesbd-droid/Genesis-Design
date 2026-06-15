from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Team, User, UserRole
from apps.core.models import CompanySettings, SLAConfiguration
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import (
    DesignComment, DesignPriority, DesignRequest, DesignStatus,
    DesignSubmission, DrawingType,
)
from apps.notifications.models import NotificationSetting
from apps.projects.models import Project, ProjectStatus


DRAWING_TYPES = [
    ('Initial Drawing', 'ID', 3),
    ('Details Drawing', 'DD', 5),
    ('LC Drawing', 'LC', 5),
    ('Shop Drawing', 'SD', 7),
    ('As Built Drawing', 'AB', 4),
    ('RSC Initial Audit Drawing', 'RIA', 5),
    ('RSC Proposed Drawing', 'RP', 5),
    ('RSC As Built Drawing', 'RAB', 4),
    ('RSC T&C Drawing', 'RTC', 5),
]

DEMO_USERS = [
    ('admin', 'admin123', 'Admin User', UserRole.ADMIN, 'ADM001'),
    ('hod', 'hod123', 'Sarah Head', UserRole.HEAD_OF_DESIGN, 'HOD001'),
    ('designer1', 'design123', 'Rahim Ahmed', UserRole.DESIGNER, 'DSG001'),
    ('designer2', 'design123', 'Rafi Karim', UserRole.DESIGNER, 'DSG002'),
    ('verifier', 'verify123', 'Karim Verifier', UserRole.VERIFICATION_TEAM, 'VER001'),
    ('requester', 'request123', 'Karim Requester', UserRole.DESIGN_REQUESTER, 'REQ001'),
]

SAMPLE_PROJECTS = [
    {
        'code': 'PRJ-001',
        'client_name': 'Tower A Residential Complex',
        'address': 'Gulshan, Dhaka',
        'description': 'High-rise residential tower — 12 design requests.',
        'status': ProjectStatus.ACTIVE,
        'design_count': 12,
    },
    {
        'code': 'PRJ-002',
        'client_name': 'City Mall-B Commercial',
        'address': 'Banani, Dhaka',
        'description': 'Commercial mall development — 8 design requests.',
        'status': ProjectStatus.ACTIVE,
        'design_count': 8,
    },
    {
        'code': 'PRJ-003',
        'client_name': 'Office Tower-C',
        'address': 'Uttara, Dhaka',
        'description': 'Completed office tower — 5 designs all done.',
        'status': ProjectStatus.COMPLETED,
        'design_count': 5,
    },
]

STATUS_POOL_ACTIVE = [
    DesignStatus.NEW_REQUEST, DesignStatus.ACKNOWLEDGED, DesignStatus.ASSIGNED,
    DesignStatus.IN_PROGRESS, DesignStatus.UNDER_REVIEW, DesignStatus.CORRECTION_REQUIRED,
    DesignStatus.VERIFICATION_PENDING, DesignStatus.APPROVED,
]
PRIORITY_POOL = [
    DesignPriority.CRITICAL, DesignPriority.HIGH, DesignPriority.MEDIUM, DesignPriority.LOW,
]


class Command(BaseCommand):
    help = 'Seed drawing types, settings, users, and sample projects with 25 designs'

    def handle(self, *args, **options):
        team, _ = Team.objects.get_or_create(name='Design Department', defaults={'department': 'Design'})

        for name, prefix, sla_days in DRAWING_TYPES:
            DrawingType.objects.update_or_create(
                name=name,
                defaults={'code_prefix': prefix, 'default_sla_days': sla_days, 'is_active': True},
            )

        CompanySettings.get_solo()
        SLAConfiguration.get_solo()
        NotificationSetting.get_solo()
        ensure_role_permissions()

        users = {}
        hod = None
        today = date.today()
        for username, password, full_name, role, emp_id in DEMO_USERS:
            first, *rest = full_name.split(' ', 1)
            last = rest[0] if rest else ''
            user, _ = User.objects.get_or_create(username=username, defaults={'email': f'{username}@genesisdesign.local'})
            user.first_name = first
            user.last_name = last
            user.role = role
            user.employee_id = emp_id
            user.team = team
            user.is_active = True
            user.status = 'active'
            user.joining_date = today - timedelta(days=365)
            user.designation = user.get_role_display()
            user.department = 'Design'
            user.set_password(password)
            if role == UserRole.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            user.save()
            users[username] = user
            if role == UserRole.HEAD_OF_DESIGN:
                hod = user

        if hod:
            User.objects.filter(role=UserRole.DESIGNER).update(manager=hod)

        requester = users['requester']
        designer1 = users['designer1']
        designer2 = users['designer2']
        verifier = users['verifier']
        now = timezone.now()
        drawing_types = list(DrawingType.objects.filter(is_active=True))

        revision_design = None
        total_designs = 0

        for i, pdata in enumerate(SAMPLE_PROJECTS):
            project, _ = Project.objects.update_or_create(
                code=pdata['code'],
                defaults={
                    'name': pdata['client_name'],
                    'client_name': pdata['client_name'],
                    'address': pdata['address'],
                    'description': pdata['description'],
                    'start_date': today - timedelta(days=60 + i * 15),
                    'expected_completion_date': today + timedelta(days=120 - i * 20),
                    'status': pdata['status'],
                    'created_by': requester,
                    'health_score': 90 - i * 8,
                },
            )

            DesignRequest.objects.filter(project=project).delete()

            for seq in range(1, pdata['design_count'] + 1):
                dt = drawing_types[(seq + i) % len(drawing_types)]
                if pdata['status'] == ProjectStatus.COMPLETED:
                    status = DesignStatus.COMPLETED
                else:
                    status = STATUS_POOL_ACTIVE[(seq + i) % len(STATUS_POOL_ACTIVE)]

                designer = designer1 if seq % 2 else designer2
                priority = PRIORITY_POOL[seq % len(PRIORITY_POOL)]
                overdue = status == DesignStatus.IN_PROGRESS and seq <= 2
                due = now - timedelta(days=2) if overdue else now + timedelta(days=seq + 3)
                sla_status = 'red' if overdue else ('yellow' if seq % 5 == 0 else 'green')

                design = DesignRequest(
                    project=project,
                    drawing_type=dt,
                    sequence_number=seq,
                    priority=priority,
                    status=status,
                    requested_by=requester,
                    assigned_designer=designer if status != DesignStatus.NEW_REQUEST else None,
                    assigned_by=hod if status != DesignStatus.NEW_REQUEST else None,
                    current_holder=hod if status in (DesignStatus.NEW_REQUEST, DesignStatus.UNDER_REVIEW) else (
                        verifier if status == DesignStatus.VERIFICATION_PENDING else designer
                    ),
                    due_date=due,
                    sla_start=now - timedelta(days=10),
                    sla_due=now - timedelta(days=1) if overdue else now + timedelta(days=5),
                    sla_status=sla_status,
                    target_completion_date=today + timedelta(days=20 + seq),
                    request_message=f'Sample {dt.name} for {project.code}',
                    revision_count=0,
                    delay_source='designer' if overdue else '',
                    delay_duration_days=2 if overdue else 0,
                    completion_date=now - timedelta(days=5) if status == DesignStatus.COMPLETED else None,
                )
                design.save()
                total_designs += 1

                if seq == 3 and i == 0 and not revision_design:
                    revision_design = design
                    design.status = DesignStatus.UNDER_REVIEW
                    design.revision_count = 3
                    design.save()
                    for ver, note, accepted in [
                        (1, 'Column dimensions wrong', False),
                        (2, 'Scale issue on level 3', False),
                        (3, 'Final version — all corrections addressed', True),
                    ]:
                        DesignSubmission.objects.get_or_create(
                            design=design,
                            version_number=ver,
                            defaults={
                                'submitted_by': designer1,
                                'notes': note,
                                'internal_file_reference': f'REF-{project.code}-V{ver}',
                                'approval_status': 'Accepted' if accepted else 'Correction Required',
                            },
                        )

        if revision_design:
            DesignComment.objects.get_or_create(
                design=revision_design,
                author=hod,
                defaults={'message': '@designer1 Please check column dimensions on level 3 carefully.'},
            )
            comment = DesignComment.objects.filter(design=revision_design, author=hod).first()
            if comment:
                comment.mentions.add(designer1)

        first = DesignRequest.objects.filter(project__code='PRJ-001').first()
        if first:
            DesignComment.objects.get_or_create(
                design=first, author=requester,
                defaults={'message': 'Need this urgently for client presentation.'},
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(SAMPLE_PROJECTS)} projects, {total_designs} designs, settings, and demo users'
        ))
