from django.test import TestCase

from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.designs.progress import build_progress_steps
from apps.projects.models import Project
from apps.accounts.models import User, UserRole
from datetime import date


class ProgressStepsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.drawing_type = DrawingType.objects.create(name='ID', code_prefix='ID', allowed_days=3)
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C', start_date=date.today(), created_by=self.user,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.user,
            status=DesignStatus.NEW_REQUEST,
        )

    def _active_step(self, design):
        steps, _ = build_progress_steps(design)
        return next(s for s in steps if s['state'] == 'active')

    def test_engineer_pending_ack_shows_request_submitted(self):
        self.design.status = DesignStatus.ENGINEER_PENDING_ACK
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'submitted')
        self.assertEqual(active['label'], 'Request Submitted')

    def test_engineer_in_progress_shows_site_verification(self):
        self.design.status = DesignStatus.ENGINEER_IN_PROGRESS
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'site_engineer')
        self.assertEqual(active['label'], 'Site Verification')

    def test_new_request_shows_hod_acknowledgement(self):
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'hod_ack')
        self.assertEqual(active['label'], 'HOD Acknowledgement')

    def test_acknowledged_shows_pending_assignment(self):
        self.design.status = DesignStatus.ACKNOWLEDGED
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'assigned')
        self.assertEqual(active['label'], 'Pending Assignment')

    def test_assigned_shows_designer_assigned(self):
        self.design.status = DesignStatus.ASSIGNED
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'assigned')
        self.assertEqual(active['label'], 'Designer Assigned')

    def test_correction_required_shows_under_review_active(self):
        self.design.status = DesignStatus.CORRECTION_REQUIRED
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active']
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['key'], 'under_review')

    def test_verification_correction_shows_verification_pending_active(self):
        self.design.status = DesignStatus.VERIFICATION_CORRECTION
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active'][0]
        self.assertEqual(active['key'], 'verification_pending')

    def test_completed_marks_all_prior_steps_done(self):
        self.design.status = DesignStatus.COMPLETED
        steps, _ = build_progress_steps(self.design)
        self.assertEqual(len(steps), 10)
        self.assertEqual(steps[-1]['state'], 'active')
        self.assertTrue(all(step['state'] == 'completed' for step in steps[:-1]))

    def test_cancelled_grays_out_steps(self):
        self.design.status = DesignStatus.CANCELLED
        steps, cancelled = build_progress_steps(self.design)
        self.assertTrue(cancelled)
        self.assertTrue(all(step['state'] == 'upcoming' for step in steps))

    def test_early_pipeline_order(self):
        self.design.status = DesignStatus.ENGINEER_PENDING_ACK
        steps, _ = build_progress_steps(self.design)
        labels = [s['label'] for s in steps[:4]]
        self.assertEqual(labels, [
            'Request Submitted',
            'Site Verification',
            'HOD Acknowledgement',
            'Designer Assigned',
        ])
