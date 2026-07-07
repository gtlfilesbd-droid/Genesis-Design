"""Tests for Genesis_Workflow_Bugfix.md issues."""
from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.models import ActivityLog
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.notifications.models import Notification
from apps.notifications.services import notify_workflow_transition
from apps.permissions.services import PermissionService
from apps.projects.models import Project
from apps.workflow.permissions import design_action_flags
from apps.workflow.services import WorkflowError, transition


def _send_to_verification(design, hod, verifier, due_date=None):
    due = due_date or timezone.now() + timedelta(days=2)
    transition(
        design, 'send_to_verification', hod,
        verifier=verifier, due_date=due, comments='Please verify',
    )
    transition(design, 'accept_verification', verifier)


def _send_to_compliance(design, hod, officer, due_date=None):
    due = due_date or timezone.now() + timedelta(days=2)
    transition(
        design, 'send_to_compliance', hod,
        compliance_officer=officer, due_date=due, comments='Compliance review',
    )
    transition(design, 'accept_compliance', officer)


class WorkflowBugfixTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
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
            status=DesignStatus.NEW_REQUEST,
            current_holder=self.hod,
        )

    def test_requester_cannot_cancel_after_acknowledge(self):
        transition(self.design, 'acknowledge', self.hod)
        self.design.refresh_from_db()
        flags = design_action_flags(self.requester, self.design)
        self.assertFalse(flags['can_cancel_request'])

        self.client.login(username='req', password='pass')
        response = self.client.post(
            reverse('requests:cancel', kwargs={'pk': self.design.pk}),
            {'comments': 'Too late'},
        )
        self.assertEqual(response.status_code, 302)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.ACKNOWLEDGED)

    def test_hod_in_assignable_designers(self):
        designers = PermissionService.get_assignable_designers(self.project)
        self.assertIn(self.hod, designers)
        self.assertIn(self.designer, designers)

    def test_admin_not_in_assignable_designers(self):
        admin = User.objects.create_user(
            username='adm', password='pass', role=UserRole.ADMIN, employee_id='A001',
        )
        designers = PermissionService.get_assignable_designers(self.project)
        self.assertNotIn(admin, designers)

    def test_assign_page_lists_designers_in_dropdown(self):
        transition(self.design, 'acknowledge', self.hod)
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('workflow:assign', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.designer.get_full_name() or self.designer.username, content)
        self.assertIn(self.hod.get_full_name() or self.hod.username, content)

    def test_workflow_action_assign_lists_designers(self):
        transition(self.design, 'acknowledge', self.hod)
        self.client.login(username='hod', password='pass')
        response = self.client.get(
            reverse('workflow:action', kwargs={'pk': self.design.pk, 'action': 'assign'}),
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.designer.get_full_name() or self.designer.username, content)

    def test_send_to_verification_requires_due_date(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        with self.assertRaises(WorkflowError):
            transition(
                self.design, 'send_to_verification', self.hod,
                verifier=self.verifier, comments='No due date',
            )

    def test_verifier_acknowledge_before_active_review(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        due = timezone.now() + timedelta(days=3)
        transition(
            self.design, 'send_to_verification', self.hod,
            verifier=self.verifier, due_date=due, comments='Verify',
        )
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.VERIFICATION_PENDING_ACK)
        self.assertIsNone(self.design.verification_acknowledged_at)
        self.assertEqual(self.design.verification_due_date, due)

        transition(self.design, 'accept_verification', self.verifier)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.VERIFICATION_PENDING)
        self.assertIsNotNone(self.design.verification_acknowledged_at)
        self.assertTrue(
            Notification.objects.filter(
                user=self.hod, title__contains='Verification Acknowledged',
            ).exists()
        )

    def test_verifier_accept_notifies_hod_and_logs_activity(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        _send_to_verification(self.design, self.hod, self.verifier)
        transition(self.design, 'verify_approved', self.verifier, comments='OK')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.AWAITING_COMPLIANCE)
        self.assertTrue(
            Notification.objects.filter(
                user=self.hod, title__contains='Verification Approved',
            ).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                entity_type='design_request',
                entity_id=self.design.pk,
                action='verify_approved',
            ).exists()
        )

    def test_verifier_in_filter_after_awaiting_compliance(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        _send_to_verification(self.design, self.hod, self.verifier)
        transition(self.design, 'verify_approved', self.verifier, comments='OK')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.AWAITING_COMPLIANCE)
        visible = PermissionService.filter_design_requests(self.verifier)
        self.assertIn(self.design, visible)

    def test_verifier_can_view_request_after_verify_approved(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        _send_to_verification(self.design, self.hod, self.verifier)
        transition(self.design, 'verify_approved', self.verifier, comments='OK')
        self.client.login(username='ver', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'You do not have access to this design request.')

    def test_hod_fast_complete_visible_at_awaiting_compliance(self):
        self.design.status = DesignStatus.AWAITING_COMPLIANCE
        self.design.save()
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('workflow:action', kwargs={
            'pk': self.design.pk, 'action': 'hod_fast_complete',
        }))

    def test_detail_shows_activity_history(self):
        from apps.core.utils import log_activity
        log_activity(
            'design_request', self.design.pk, self.hod, 'verify_approved',
            'Sarah Ahmed approved the design after verification',
        )
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Activity History')
        self.assertContains(response, 'approved the design after verification')
        self.assertNotContains(response, 'No notifications for this request.')

    def test_requester_can_view_own_design_after_verify_approved(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.save()
        _send_to_verification(self.design, self.hod, self.verifier)
        transition(self.design, 'verify_approved', self.verifier, comments='OK')
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.AWAITING_COMPLIANCE)
        visible = PermissionService.filter_design_requests(self.requester)
        self.assertIn(self.design, visible)
        self.client.login(username='req', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.design.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'You do not have access to this design request.')

    def test_requester_sees_designs_on_owned_project(self):
        other_requester = User.objects.create_user(
            username='req2', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R002',
        )
        other_design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            priority='medium',
            requested_by=other_requester,
            status=DesignStatus.NEW_REQUEST,
            current_holder=self.hod,
        )
        visible = PermissionService.filter_design_requests(self.requester)
        self.assertIn(other_design, visible)
        self.client.login(username='req', password='pass')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': other_design.pk}))
        self.assertEqual(response.status_code, 200)

    def test_full_verification_compliance_chain(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.assigned_designer = self.designer
        self.design.save()
        _send_to_verification(self.design, self.hod, self.verifier)
        transition(self.design, 'verify_approved', self.verifier)
        _send_to_compliance(self.design, self.hod, self.compliance)
        transition(self.design, 'compliance_approved', self.compliance)
        self.design.refresh_from_db()
        self.assertEqual(self.design.status, DesignStatus.APPROVED)

    def test_hod_not_assigned_cannot_submit(self):
        self.design.status = DesignStatus.IN_PROGRESS
        self.design.assigned_designer = self.designer
        self.design.save()
        self.assertFalse(design_action_flags(self.hod, self.design)['can_submit_work'])
