from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.models import (
    DesignAssignment,
    DesignPriority,
    DesignRequest,
    DesignStatus,
    DrawingType,
)
from apps.projects.models import Project


class Command(BaseCommand):
    help = (
        'Create/update DEMO-LC-2V5: designer held 2 days, request 5 days past target '
        '(for lifecycle card banner testing)'
    )

    def handle(self, *args, **options):
        now = timezone.now()
        today = date.today()

        project = Project.objects.filter(code='PRJ-001').first()
        if not project:
            self.stderr.write(self.style.ERROR('PRJ-001 not found — run: python manage.py seed_data'))
            return

        hod = User.objects.filter(role=UserRole.HEAD_OF_DESIGN, is_active=True).first()
        designer = User.objects.filter(username='designer1').first()
        requester = User.objects.filter(role=UserRole.DESIGN_REQUESTER, is_active=True).first()
        drawing_type = DrawingType.objects.filter(is_active=True, code_prefix='LC').first()
        if not drawing_type:
            drawing_type = DrawingType.objects.filter(is_active=True).first()

        if not all([hod, designer, requester, drawing_type]):
            self.stderr.write(self.style.ERROR('Missing users or drawing type — run: python manage.py seed_data'))
            return

        person_hold_days = 2
        request_overdue_days = 5
        assigned_at = now - timedelta(days=person_hold_days)
        acknowledged_at = assigned_at - timedelta(days=3)
        target_date = today - timedelta(days=request_overdue_days)

        design, _created = DesignRequest.objects.update_or_create(
            design_number='DEMO-LC-2V5',
            defaults={
                'project': project,
                'drawing_type': drawing_type,
                'sequence_number': 99,
                'priority': DesignPriority.HIGH,
                'status': DesignStatus.IN_PROGRESS,
                'requested_by': requester,
                'assigned_designer': designer,
                'assigned_by': hod,
                'current_holder': designer,
                'target_completion_date': target_date,
                'due_date': now + timedelta(days=30),
                'deadline_start': acknowledged_at,
                'deadline_due': now + timedelta(days=10),
                'request_message': (
                    'Lifecycle banner demo: Waiting on designer 2 days, '
                    'request 5 days past target.'
                ),
            },
        )

        design.assignments.all().delete()
        assignment = DesignAssignment.objects.create(
            design=design,
            designer=designer,
            assigned_by=hod,
            due_date=now + timedelta(days=30),
            instructions='Demo assignment — HOD due is later than requester target.',
        )
        DesignAssignment.objects.filter(pk=assignment.pk).update(assigned_at=assigned_at)
        assignment.refresh_from_db()

        self.stdout.write(self.style.SUCCESS(
            f'Lifecycle demo ready: {design.design_number} (pk={design.pk})\n'
            f'  Waiting on: {designer.get_full_name()} · since {assignment.assigned_at:%d %b, %I:%M %p} (~{person_hold_days} days)\n'
            f'  Past target: deadline {target_date:%d %b %Y} (~{request_overdue_days} days)\n'
            f'  Open: /designs/{design.pk}/'
        ))
