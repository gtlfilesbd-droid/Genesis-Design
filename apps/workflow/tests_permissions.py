from datetime import date

from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project
from apps.workflow.permissions import can_run_workflow_action, design_action_flags


class WorkflowPermissionTests(TestCase):
    def setUp(self):
        self.hod = User.objects.create_user(
            username='hod', password='hod123', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.drawing_type = DrawingType.objects.create(name='ID', code_prefix='ID', allowed_days=3)
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.UNDER_REVIEW,
            current_holder=self.hod,
        )

    def test_hod_can_review_without_project_membership(self):
        self.assertTrue(
            can_run_workflow_action(self.hod, self.project, 'send_to_verification', 'PROJECT_PERM_REVIEW')
        )
        flags = design_action_flags(self.hod, self.design)
        self.assertTrue(flags['can_send_to_verification'])

    def test_hod_sees_review_actions_on_detail_page(self):
        client = Client()
        self.hod.status = 'active'
        self.hod.save(update_fields=['status'])
        client.login(username='hod', password='hod123')
        response = client.get(reverse('requests:detail', args=[self.design.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send to Verification')
        self.assertContains(response, 'Request Correction')

    def test_hod_can_review_when_status_submitted(self):
        self.design.status = DesignStatus.SUBMITTED
        self.design.save(update_fields=['status'])
        client = Client()
        self.hod.status = 'active'
        self.hod.save(update_fields=['status'])
        client.login(username='hod', password='hod123')
        response = client.get(reverse('requests:detail', args=[self.design.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send to Verification')
