from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.models import DesignAssignment, DesignRequest, DesignStatus, DrawingType
from apps.designs.timer_helpers import (
    get_completion_timeline_data,
    get_deadline_timer_data,
    get_time_breakdown_data,
)
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

    def test_deadline_timer_for_new_request_hod_ack_sla(self):
        timer = get_deadline_timer_data(self.design)
        self.assertIsNotNone(timer)
        self.assertFalse(timer['is_overdue'])

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

    def test_completion_timeline_none_for_unassigned_request(self):
        self.assertIsNone(get_completion_timeline_data(self.design))

    def test_completion_timeline_designer_stage_only(self):
        now = timezone.now()
        self.design.status = DesignStatus.IN_PROGRESS
        self.design.target_completion_date = (now + timedelta(days=5)).date()
        self.design.save()
        assignment = DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.requester,
        )
        assignment.assigned_at = now - timedelta(days=2)
        assignment.save(update_fields=['assigned_at'])

        timeline = get_completion_timeline_data(self.design)
        self.assertIsNotNone(timeline)
        self.assertEqual(len(timeline['stages']), 1)
        self.assertEqual(timeline['stages'][0]['name'], 'Designer')
        self.assertTrue(timeline['stages'][0]['is_ongoing'])
        self.assertFalse(timeline['is_overdue'])

    def test_completion_timeline_overdue_marks_ongoing_stage(self):
        now = timezone.now()
        self.design.status = DesignStatus.IN_PROGRESS
        self.design.target_completion_date = (now - timedelta(days=2)).date()
        self.design.save()
        assignment = DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.requester,
        )
        assignment.assigned_at = now - timedelta(days=5)
        assignment.save(update_fields=['assigned_at'])

        timeline = get_completion_timeline_data(self.design)
        self.assertTrue(timeline['is_overdue'])
        self.assertTrue(timeline['stages'][0]['is_current_delay_source'])
        self.assertEqual(timeline['stages'][0]['segment_class'], 'segment-delay')

    def test_completion_timeline_completed_on_time(self):
        now = timezone.now()
        self.design.status = DesignStatus.COMPLETED
        self.design.target_completion_date = (now + timedelta(days=1)).date()
        self.design.completion_date = now
        self.design.save()
        assignment = DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.requester,
        )
        assignment.assigned_at = now - timedelta(days=3)
        assignment.save(update_fields=['assigned_at'])

        timeline = get_completion_timeline_data(self.design)
        self.assertTrue(timeline['is_completed_on_time'])
        self.assertFalse(timeline['is_overdue'])
        self.assertIsNone(timeline['delay_info'])
