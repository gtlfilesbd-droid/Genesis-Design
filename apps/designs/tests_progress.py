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

    def _assert_continuous_completed_line(self, steps):
        active_index = next(i for i, s in enumerate(steps) if s['state'] == 'active')
        for index, step in enumerate(steps):
            if index < active_index:
                self.assertEqual(step['state'], 'completed', msg=f"step {step['key']} should be completed")
            elif index == active_index:
                self.assertEqual(step['state'], 'active')
            else:
                self.assertEqual(step['state'], 'upcoming', msg=f"step {step['key']} should be upcoming")

    def test_engineer_pending_ack_shows_site_verification(self):
        self.design.status = DesignStatus.ENGINEER_PENDING_ACK
        self.design.assigned_site_engineer_id = self.user.pk
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'site_engineer')
        self.assertEqual(active['label'], 'Site Verification')

    def test_request_under_review_shows_under_review_step(self):
        self.design.status = DesignStatus.REQUEST_UNDER_REVIEW
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'request_under_review')
        self.assertEqual(active['label'], 'Under Review')

    def test_engineer_in_progress_shows_site_verification(self):
        self.design.status = DesignStatus.ENGINEER_IN_PROGRESS
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'site_engineer')
        self.assertEqual(active['label'], 'Site Verification')

    def test_new_request_waits_on_submitted_before_hod_ack(self):
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'submitted')
        self.assertEqual(active['label'], 'Request Submitted')
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'upcoming')

    def test_new_request_hod_ack_not_completed_before_acknowledge(self):
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'upcoming')
        self.assertFalse(self.design.deadline_start)
        self._assert_continuous_completed_line(steps)

    def test_new_request_after_engineer_submit_waits_on_site_verification(self):
        from django.utils import timezone
        engineer = User.objects.create_user(
            username='eng', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='E1',
        )
        self.design.assigned_site_engineer = engineer
        self.design.engineer_submitted_at = timezone.now()
        self.design.save()
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'site_engineer')
        self.assertEqual(active['label'], 'Site Verification')
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'upcoming')
        self._assert_continuous_completed_line(steps)

    def test_engineer_in_progress_hod_ack_is_upcoming(self):
        self.design.status = DesignStatus.ENGINEER_IN_PROGRESS
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'upcoming')
        site_step = next(s for s in steps if s['key'] == 'site_engineer')
        self.assertEqual(site_step['state'], 'active')
        self._assert_continuous_completed_line(steps)

    def test_acknowledged_shows_hod_acknowledgement_active(self):
        from django.utils import timezone
        self.design.status = DesignStatus.ACKNOWLEDGED
        self.design.deadline_start = timezone.now()
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'active')
        self._assert_continuous_completed_line(steps)

    def test_acknowledged_designer_assigned_is_upcoming(self):
        self.design.status = DesignStatus.ACKNOWLEDGED
        steps, _ = build_progress_steps(self.design)
        assigned_step = next(s for s in steps if s['key'] == 'assigned')
        self.assertEqual(assigned_step['state'], 'upcoming')
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'hod_ack')
        self.assertEqual(active['label'], 'HOD Acknowledgement')

    def test_assigned_shows_designer_assigned(self):
        self.design.status = DesignStatus.ASSIGNED
        active = self._active_step(self.design)
        self.assertEqual(active['key'], 'assigned')
        self.assertEqual(active['label'], 'Designer Assigned')
        steps, _ = build_progress_steps(self.design)
        hod_step = next(s for s in steps if s['key'] == 'hod_ack')
        self.assertEqual(hod_step['state'], 'completed')
        self._assert_continuous_completed_line(steps)

    def test_correction_required_shows_under_review_active(self):
        self.design.status = DesignStatus.CORRECTION_REQUIRED
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active']
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['key'], 'under_review')
        self._assert_continuous_completed_line(steps)

    def test_verification_correction_shows_verification_pending_active(self):
        self.design.status = DesignStatus.VERIFICATION_CORRECTION
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active'][0]
        self.assertEqual(active['key'], 'verification_pending')
        self._assert_continuous_completed_line(steps)

    def test_completed_marks_all_prior_steps_done(self):
        self.design.status = DesignStatus.COMPLETED
        steps, _ = build_progress_steps(self.design)
        self.assertEqual(len(steps), 11)
        self.assertEqual(steps[-1]['state'], 'active')
        self.assertTrue(all(step['state'] == 'completed' for step in steps[:-1]))
        self._assert_continuous_completed_line(steps)

    def test_cancelled_grays_out_steps(self):
        self.design.status = DesignStatus.CANCELLED
        steps, cancelled = build_progress_steps(self.design)
        self.assertTrue(cancelled)
        self.assertTrue(all(step['state'] == 'upcoming' for step in steps))

    def test_early_pipeline_order(self):
        self.design.status = DesignStatus.ENGINEER_PENDING_ACK
        steps, _ = build_progress_steps(self.design)
        labels = [s['label'] for s in steps[:5]]
        self.assertEqual(labels, [
            'Request Submitted',
            'Under Review',
            'Site Verification',
            'HOD Acknowledgement',
            'Designer Assigned',
        ])
