from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.permissions.services import PermissionService
from apps.projects.models import Project
from apps.workflow.permissions import can_user_submit_work, design_action_flags
from apps.workflow.services import transition


class WorkflowFixesTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
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
            status=DesignStatus.IN_PROGRESS,
            current_holder=self.designer,
        )

    def test_hod_not_assigned_cannot_submit_work(self):
        self.assertFalse(can_user_submit_work(self.hod, self.design))
        flags = design_action_flags(self.hod, self.design)
        self.assertFalse(flags['can_submit_work'])

    def test_assigned_designer_can_submit_work(self):
        self.assertTrue(can_user_submit_work(self.designer, self.design))

    def test_hod_self_assign_goes_in_progress(self):
        design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            priority='medium',
            requested_by=self.requester,
            status=DesignStatus.ACKNOWLEDGED,
            current_holder=self.hod,
        )
        transition(design, 'assign', self.hod, designer=self.hod)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.IN_PROGRESS)
        self.assertEqual(design.assigned_designer, self.hod)
        self.assertTrue(can_user_submit_work(self.hod, design))

    def test_verifier_sees_project_when_assigned(self):
        self.design.assigned_verifier = self.verifier
        self.design.status = DesignStatus.VERIFICATION_PENDING
        self.design.save()
        projects = PermissionService.get_user_projects(self.verifier)
        self.assertIn(self.project, projects)
        self.assertTrue(
            PermissionService.has_project_permission(
                self.verifier, self.project, 'PROJECT_PERM_VIEW',
            )
        )

    def test_hod_in_assignable_designers(self):
        designers = PermissionService.get_assignable_designers(self.project)
        self.assertIn(self.hod, designers)


class NotificationApiTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.user = User.objects.create_user(
            username='apiuser', password='pass', role=UserRole.DESIGNER, employee_id='A001',
        )
        self.client = Client()

    def test_unread_count_requires_login(self):
        response = self.client.get(reverse('api:notification_unread_count'))
        self.assertEqual(response.status_code, 302)

    def test_unread_count_json(self):
        from apps.notifications.models import Notification
        Notification.objects.create(user=self.user, title='Test', message='Hello')
        self.client.login(username='apiuser', password='pass')
        response = self.client.get(reverse('api:notification_unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_badge_fragment(self):
        from apps.notifications.models import Notification
        Notification.objects.create(user=self.user, title='Test', message='Hello')
        self.client.login(username='apiuser', password='pass')
        response = self.client.get(reverse('api:notification_badge'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'1', response.content)
