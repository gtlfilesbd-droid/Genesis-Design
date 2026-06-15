from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.designs.progress import build_progress_steps
from apps.projects.models import Project
from apps.workflow.services import WorkflowError, transition


class SRSWorkflowFlowTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R001',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H001',
        )
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D001',
        )
        self.verifier = User.objects.create_user(
            username='ver', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='V001',
        )
        self.compliance = User.objects.create_user(
            username='cmp', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='C001',
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.project = Project.objects.create(
            name='Test Project', code='PRJ-001', client_name='Client',
            start_date=date.today(), created_by=self.requester,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            priority='medium',
            requested_by=self.requester,
            assigned_designer=self.designer,
            status=DesignStatus.UNDER_REVIEW,
            current_holder=self.hod,
        )

    def test_hod_send_to_verification_then_verifier_accepts(self):
        transition(
            self.design, 'send_to_verification', self.hod,
            verifier=self.verifier, comments='Please verify',
        )
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.VERIFICATION_PENDING)
        self.assertEqual(self.design.assigned_verifier, self.verifier)

        transition(self.design, 'verify_approved', self.verifier, comments='OK')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.AWAITING_COMPLIANCE)

    def test_verifier_correction_loop_increments_revision_on_forward(self):
        transition(
            self.design, 'send_to_verification', self.hod,
            verifier=self.verifier, comments='Verify',
        )
        transition(self.design, 'verification_correction', self.verifier, comments='Fix dims')
        self.design.refresh_from_db()
        self.assertEqual(self.design.revision_count, 0)

        transition(self.design, 'forward_to_designer', self.hod)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.CORRECTION_REQUIRED)
        self.assertEqual(self.design.revision_count, 1)

        transition(self.design, 'resubmit', self.designer)
        transition(self.design, 'submit_work', self.designer, notes='Fixed')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.UNDER_REVIEW)

        transition(
            self.design, 'send_to_verification', self.hod,
            verifier=self.verifier, comments='Re-verify',
        )
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.VERIFICATION_PENDING)

    def test_full_path_through_compliance(self):
        transition(
            self.design, 'send_to_verification', self.hod,
            verifier=self.verifier, comments='Verify',
        )
        transition(self.design, 'verify_approved', self.verifier)
        transition(
            self.design, 'send_to_compliance', self.hod,
            compliance_officer=self.compliance, comments='Compliance check',
        )
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.COMPLIANCE_PENDING)
        self.assertEqual(self.design.assigned_compliance_officer, self.compliance)

        transition(self.design, 'compliance_approved', self.compliance, comments='Approved')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.APPROVED)

        transition(self.design, 'complete', self.hod)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.COMPLETED)

    def test_hod_fast_complete_sets_skip_flags(self):
        transition(self.design, 'hod_fast_complete', self.hod)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.COMPLETED)
        self.assertTrue(self.design.verification_skipped_by_hod)
        self.assertTrue(self.design.compliance_skipped_by_hod)

    def test_progress_bar_maps_correction_substates(self):
        self.design.status = DesignStatus.VERIFICATION_CORRECTION
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active'][0]
        self.assertEqual(active['key'], 'verification_pending')

        self.design.status = DesignStatus.AWAITING_COMPLIANCE
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active'][0]
        self.assertEqual(active['key'], 'compliance_pending')

        self.design.status = DesignStatus.COMPLIANCE_CORRECTION
        steps, _ = build_progress_steps(self.design)
        active = [s for s in steps if s['state'] == 'active'][0]
        self.assertEqual(active['key'], 'compliance_pending')

    def test_send_to_verification_requires_verifier(self):
        with self.assertRaises(WorkflowError):
            transition(self.design, 'send_to_verification', self.hod, comments='No verifier')
