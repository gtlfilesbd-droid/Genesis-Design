from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.lifecycle_timeline import (
    build_lifecycle_data,
    build_timeline_segments,
    get_current_delay_info,
    get_lifecycle_timeline_data,
)
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project
from apps.workflow.services import transition


class LifecycleTimelineTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req',
            password='pass',
            role=UserRole.DESIGN_REQUESTER,
            employee_id='R001',
        )
        self.hod = User.objects.create_user(
            username='hod',
            password='pass',
            role=UserRole.HEAD_OF_DESIGN,
            employee_id='H001',
            first_name='Head',
            last_name='Design',
        )
        self.designer = User.objects.create_user(
            username='designer1',
            password='pass',
            role=UserRole.DESIGNER,
            employee_id='D001',
            first_name='Rahim',
            last_name='Designer',
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
            target_completion_date=date.today() + timedelta(days=10),
        )

    def test_new_request_shows_awaiting_ack_and_pending_chain(self):
        data = build_lifecycle_data(self.design)
        self.assertIsNotNone(data)
        labels = [s['label'] for s in data['segments']]
        self.assertIn('Acknowledgement', labels)

    def test_build_lifecycle_data_stats(self):
        data = build_lifecycle_data(self.design)
        self.assertIsNotNone(data['total_days'])
        self.assertEqual(data['current_stage_label'], 'Acknowledgement')

    def test_unacknowledged_delay_info_points_to_hod(self):
        self.design.target_completion_date = date.today() - timedelta(days=1)
        self.design.save(update_fields=['target_completion_date'])
        delay = get_current_delay_info(self.design)
        self.assertIsNotNone(delay)
        self.assertIn('Acknowledgement', delay['current_stage_label'])
        self.assertTrue(delay['is_overdue'])

    def test_acknowledge_assign_designer_flow(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=3),
        )
        transition(self.design, 'accept_assignment', self.designer)

        segments = build_timeline_segments(self.design)
        labels = [s['label'] for s in segments if not s.get('is_pending')]
        self.assertTrue(any('Assign' in label or 'Designer' in label for label in labels))

    def test_correction_creates_multiple_designer_segments(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=3),
        )
        transition(self.design, 'accept_assignment', self.designer)
        transition(self.design, 'submit_work', self.designer, comments='V1')
        transition(self.design, 'request_correction', self.hod, comments='Fix')
        transition(self.design, 'resubmit', self.designer, comments='V2')

        segments = build_timeline_segments(self.design)
        designer_labels = [s['label'] for s in segments if s['role'] == 'designer' and not s.get('is_pending')]
        self.assertGreaterEqual(len(designer_labels), +2)

    def test_completed_on_time_shows_green_status(self):
        transition(self.design, 'acknowledge', self.hod)
        self.design.target_completion_date = date.today() + timedelta(days=30)
        self.design.completion_date = timezone.now()
        self.design.status = DesignStatus.COMPLETED
        self.design.save()

        data = get_lifecycle_timeline_data(self.design)
        self.assertTrue(data['is_completed_on_time'])
        self.assertIsNone(data['delay_info'])
