from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta

from apps.accounts.models import User, UserRole
from apps.designs.models import DrawingType, DesignRequest, DesignStatus
from apps.projects.models import Project
from apps.workflow.services import WorkflowError, transition


class WorkflowTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER,
            employee_id='R001',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN,
            employee_id='H001',
        )
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER,
            employee_id='D001',
        )
        self.verifier = User.objects.create_user(
            username='ver', password='pass', role=UserRole.VERIFICATION_TEAM,
            employee_id='V001',
        )
        self.compliance = User.objects.create_user(
            username='cmp', password='pass', role=UserRole.COMPLIANCE_TEAM,
            employee_id='C001',
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
            status=DesignStatus.NEW_REQUEST,
            current_holder=self.hod,
        )

    def test_full_workflow(self):
        transition(self.design, 'acknowledge', self.hod)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.ACKNOWLEDGED)
        self.assertIsNotNone(self.design.deadline_start)

        transition(self.design, 'assign', self.hod, designer=self.designer,
                   due_date=timezone.now() + timedelta(days=3))
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.ASSIGNED)
        self.assertEqual(self.design.assigned_designer, self.designer)

        transition(self.design, 'accept_assignment', self.designer)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.IN_PROGRESS)

        transition(
            self.design, 'submit_work', self.designer,
            file_name='ID-01.dwg',
            revision_date=timezone.localdate(),
            notes='Done',
        )
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.UNDER_REVIEW)

        transition(self.design, 'send_to_verification', self.hod,
                   verifier=self.verifier, comments='Ready for verification')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.VERIFICATION_PENDING)

        transition(self.design, 'verify_approved', self.verifier)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.AWAITING_COMPLIANCE)

        transition(self.design, 'send_to_compliance', self.hod,
                   compliance_officer=self.compliance, comments='Compliance review')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.COMPLIANCE_PENDING)

        transition(self.design, 'compliance_approved', self.compliance)

        transition(self.design, 'complete', self.hod)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.COMPLETED)
        self.assertIsNotNone(self.design.completion_date)

    def test_design_number_generation(self):
        self.assertTrue(self.design.design_number.startswith('PRJ-001-ID-'))

    def test_permission_denied(self):
        with self.assertRaises(WorkflowError):
            transition(self.design, 'acknowledge', self.designer)


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN,
        )

    def test_login_redirects_to_role_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'hod', 'password': 'pass',
        })
        self.assertRedirects(response, reverse('accounts:hod_dashboard'))
