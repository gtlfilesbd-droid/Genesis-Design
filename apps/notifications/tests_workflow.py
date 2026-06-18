from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService, notify_workflow_transition
from apps.projects.models import Project


class NotificationServiceTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        )
        self.drawing_type = DrawingType.objects.create(name='ID', code_prefix='ID', allowed_days=3)
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.NEW_REQUEST,
        )

    def test_on_request_created_notifies_assign_users(self):
        NotificationService.on_request_created(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.hod, title__contains='New Design Request').exists()
        )

    def test_on_request_acknowledged_notifies_requester(self):
        NotificationService.on_request_acknowledged(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Acknowledged').exists()
        )

    def test_notify_workflow_transition_maps_acknowledge(self):
        notify_workflow_transition(self.design, 'acknowledge', self.hod)
        self.assertEqual(
            Notification.objects.filter(user=self.requester).count(),
            1,
        )

    def test_acknowledge_notifies_project_owner(self):
        other_submitter = User.objects.create_user(
            username='sub', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R2',
        )
        self.design.requested_by = other_submitter
        self.design.save(update_fields=['requested_by'])
        NotificationService.on_request_acknowledged(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Acknowledged').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=other_submitter, title__contains='Acknowledged').exists()
        )

    def test_acknowledge_via_workflow_transition_integration(self):
        from apps.workflow.services import transition
        self.design.status = DesignStatus.NEW_REQUEST
        self.design.save(update_fields=['status', 'primary_status', 'deadline_missed'])
        transition(self.design, 'acknowledge', self.hod)
        self.assertTrue(
            Notification.objects.filter(
                user=self.requester, title__contains='Request Acknowledged',
            ).exists()
        )

    def test_verification_approved_notifies_requester(self):
        NotificationService.on_verification_approved(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Verification Approved').exists()
        )

    def test_verification_correction_notifies_requester(self):
        NotificationService.on_verification_correction(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Verification Correction').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=self.hod, title__contains='Verification Correction').exists()
        )

    def test_compliance_correction_notifies_requester(self):
        NotificationService.on_compliance_correction(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Compliance Correction').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=self.hod, title__contains='Compliance Correction').exists()
        )

    def test_on_designer_assigned_notifies_designer(self):
        self.design.assigned_designer = self.designer
        NotificationService.on_designer_assigned(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.designer, title__contains='Assignment').exists()
        )

    def test_accept_assignment_notifies_hod(self):
        self.design.assigned_designer = self.designer
        self.design.status = DesignStatus.ASSIGNED
        self.design.save()
        notify_workflow_transition(self.design, 'accept_assignment', self.designer)
        self.assertTrue(
            Notification.objects.filter(user=self.hod, title__contains='Assignment Accepted').exists()
        )
        self.assertFalse(
            Notification.objects.filter(user=self.designer, title__contains='Assignment Accepted').exists()
        )

    def test_accept_assignment_notifies_requester(self):
        self.design.assigned_designer = self.designer
        self.design.status = DesignStatus.ASSIGNED
        self.design.save()
        notify_workflow_transition(self.design, 'accept_assignment', self.designer)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Assignment Accepted').exists()
        )

    def test_submit_work_notifies_requester(self):
        self.design.assigned_designer = self.designer
        self.design.save()
        notify_workflow_transition(self.design, 'submit_work', self.designer)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Work Submitted').exists()
        )

    def test_send_to_compliance_notifies_requester(self):
        compliance = User.objects.create_user(
            username='cmp', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='C1',
        )
        self.design.assigned_compliance_officer = compliance
        self.design.current_holder = compliance
        self.design.save()
        NotificationService.on_sent_to_compliance(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Sent to Compliance').exists()
        )

    def test_completed_notifies_project_owner(self):
        other_submitter = User.objects.create_user(
            username='sub', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R2',
        )
        self.design.requested_by = other_submitter
        self.design.assigned_designer = self.designer
        self.design.save()
        NotificationService.on_completed(self.design)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Design Completed').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=other_submitter, title__contains='Design Completed').exists()
        )

    def test_workflow_chain_notifies_requester_at_key_steps(self):
        from apps.workflow.services import transition

        self.design.status = DesignStatus.NEW_REQUEST
        self.design.save(update_fields=['status', 'primary_status', 'deadline_missed'])
        transition(self.design, 'acknowledge', self.hod)
        transition(self.design, 'assign', self.hod, designer=self.designer)
        transition(self.design, 'accept_assignment', self.designer)
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Request Acknowledged').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Designer Assigned').exists()
        )
        self.assertTrue(
            Notification.objects.filter(user=self.requester, title__contains='Assignment Accepted').exists()
        )

    def test_accept_verification_notifies_hod(self):
        from apps.accounts.models import UserRole as UR
        verifier = User.objects.create_user(
            username='ver', password='pass', role=UR.VERIFICATION_TEAM, employee_id='V1',
        )
        self.design.assigned_verifier = verifier
        self.design.status = DesignStatus.VERIFICATION_PENDING_ACK
        self.design.save()
        notify_workflow_transition(self.design, 'accept_verification', verifier)
        self.assertTrue(
            Notification.objects.filter(user=self.hod, title__contains='Verification Acknowledged').exists()
        )
        self.assertFalse(
            Notification.objects.filter(user=verifier, title__contains='Verification Acknowledged').exists()
        )
