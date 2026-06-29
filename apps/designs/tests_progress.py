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

    def test_new_request_shows_hod_step_active(self):
        steps, cancelled = build_progress_steps(self.design)
        self.assertFalse(cancelled)
        self.assertEqual(steps[0]['state'], 'completed')
        self.assertEqual(steps[0]['label'], 'Site Engineer')
        self.assertEqual(steps[1]['state'], 'active')
        self.assertEqual(steps[1]['label'], 'New Request')

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
