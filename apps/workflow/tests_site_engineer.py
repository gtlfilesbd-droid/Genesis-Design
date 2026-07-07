from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.models import UserExtraPermission
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.permissions.services import PermissionService
from apps.projects.models import Project
from apps.workflow.action_sla import is_action_overdue_for_user
from apps.workflow.services import WorkflowError, transition


class SiteEngineerWorkflowTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R001',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H001',
        )
        self.engineer = User.objects.create_user(
            username='eng', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='E001',
        )
        UserExtraPermission.objects.create(user=self.engineer, can_site_engineer=True)
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.project = Project.objects.create(
            name='Test Project', code='PRJ-001', client_name='Client',
            start_date=date.today(), created_by=self.requester,
        )
        self.due = timezone.now() + timedelta(days=5)

    def _create_legacy_engineer_request(self):
        """Legacy requests that bypass the under-review stage."""
        return DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            priority='medium',
            request_message='Need site check',
            requested_by=self.requester,
            assigned_site_engineer=self.engineer,
            engineer_due_date=self.due,
            engineer_instructions='Measure all rooms',
            engineer_assigned_at=timezone.now(),
            status=DesignStatus.ENGINEER_PENDING_ACK,
            current_holder=self.engineer,
        )

    def test_get_site_engineers_excludes_admin_hod_designer(self):
        qs = PermissionService.get_site_engineers()
        self.assertIn(self.engineer, qs)
        self.assertNotIn(self.hod, qs)

    def test_legacy_create_assigns_engineer_pending_ack(self):
        design = self._create_legacy_engineer_request()
        self.assertEqual(design.status, DesignStatus.ENGINEER_PENDING_ACK)
        self.assertEqual(design.assigned_site_engineer, self.engineer)
        self.assertEqual(design.current_holder, self.engineer)
        self.assertEqual(design.engineer_due_date, self.due)

    def test_full_engineer_to_hod_path(self):
        design = self._create_legacy_engineer_request()
        transition(design, 'acknowledge_engineer', self.engineer)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.ENGINEER_IN_PROGRESS)
        self.assertIsNotNone(design.engineer_acknowledged_at)

        transition(
            design, 'submit_engineer_review', self.engineer,
            comments='All measurements verified on site',
        )
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.NEW_REQUEST)
        self.assertEqual(design.current_holder, self.hod)
        self.assertIn('measurements', design.engineer_site_notes)

        transition(design, 'acknowledge', self.hod)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.ACKNOWLEDGED)

    def test_submit_requires_notes(self):
        design = self._create_legacy_engineer_request()
        transition(design, 'acknowledge_engineer', self.engineer)
        with self.assertRaises(WorkflowError):
            transition(design, 'submit_engineer_review', self.engineer, comments='   ')

    def test_engineer_participation_visibility(self):
        design = self._create_legacy_engineer_request()
        visible = PermissionService.filter_design_requests(
            self.engineer, DesignRequest.objects.all(),
        )
        self.assertIn(design, visible)

    def test_ack_overdue_for_engineer(self):
        design = self._create_legacy_engineer_request()
        design.engineer_assigned_at = timezone.now() - timedelta(days=3)
        design.save(update_fields=['engineer_assigned_at'])
        self.assertTrue(is_action_overdue_for_user(design, self.engineer))

    def test_work_overdue_property(self):
        design = self._create_legacy_engineer_request()
        design.engineer_due_date = timezone.now() - timedelta(hours=1)
        design.save(update_fields=['engineer_due_date'])
        self.assertTrue(design.is_engineer_work_overdue)
