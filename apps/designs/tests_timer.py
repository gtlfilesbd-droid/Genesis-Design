from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.models import DesignAssignment, DesignRequest, DesignStatus, DrawingType
from apps.designs.timer_helpers import get_deadline_timer_data, get_time_breakdown_data
from apps.projects.models import Project


class TimerHelpersTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req',
            password='pass',
            role=UserRole.DESIGN_REQUESTER,
            employee_id='R001',
        )
        self.designer = User.objects.create_user(
            username='designer1',
            password='pass',
            role=UserRole.DESIGNER,
            employee_id='D001',
        )
        self.project = Project.objects.create(
            name='Test Project',
            code='TST',
            client_name='Test Client',
            start_date=date.today(),
            created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Floor Plan',
            code_prefix='FP',
            allowed_days=5,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.NEW_REQUEST,
        )

    def test_deadline_timer_none_for_new_request(self):
        self.assertIsNone(get_deadline_timer_data(self.design))

    def test_deadline_timer_for_assigned_design(self):
        now = timezone.now()
        self.design.status = DesignStatus.IN_PROGRESS
        self.design.due_date = now + timedelta(days=2)
        self.design.save()
        assignment = DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.requester,
            due_date=self.design.due_date,
        )
        assignment.assigned_at = now - timedelta(days=1)
        assignment.save(update_fields=['assigned_at'])

        timer = get_deadline_timer_data(self.design)
        self.assertIsNotNone(timer)
        self.assertGreater(timer['percent_elapsed'], 0)
        self.assertLess(timer['percent_elapsed'], 100)
        self.assertFalse(timer['is_overdue'])

    def test_time_breakdown_shows_only_completed_stages(self):
        now = timezone.now()
        self.design.deadline_start = now - timedelta(days=3)
        self.design.save(update_fields=['deadline_start'])

        breakdown = get_time_breakdown_data(self.design)
        self.assertEqual(len(breakdown['stages']), 1)
        self.assertEqual(breakdown['stages'][0]['label'], 'Request to Acknowledgement')
        self.assertIsNotNone(breakdown['total_days'])

    def test_time_breakdown_empty_for_brand_new_request(self):
        breakdown = get_time_breakdown_data(self.design)
        self.assertEqual(breakdown['stages'], [])
        self.assertIsNone(breakdown['slowest_stage'])
