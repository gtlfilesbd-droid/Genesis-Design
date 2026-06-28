from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.accounts.sidebar_permissions import get_default_sidebar_for_role
from apps.core.my_tasks_helpers import get_my_tasks_context
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.permissions.services import PermissionService
from apps.projects.models import Project


class MyTasksStatsTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        )
        self.verifier = User.objects.create_user(
            username='ver', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='V1',
        )
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.drawing_type = DrawingType.objects.create(name='Layout', code_prefix='LY', allowed_days=3)
        self.project_a = Project.objects.create(
            name='A', code='PA', client_name='Client A', start_date=date.today(),
            created_by=self.requester,
        )
        self.project_b = Project.objects.create(
            name='B', code='PB', client_name='Client B', start_date=date.today(),
            created_by=self.requester,
        )

    def _create_design(self, project, **kwargs):
        defaults = {
            'project': project,
            'drawing_type': self.drawing_type,
            'requested_by': self.requester,
            'status': DesignStatus.IN_PROGRESS,
            'assigned_designer': self.designer,
        }
        defaults.update(kwargs)
        return DesignRequest.objects.create(**defaults)

    def test_designer_stats_active_projects_overdue_and_finished(self):
        self._create_design(self.project_a, due_date=timezone.now() - timedelta(days=1))
        self._create_design(self.project_b, due_date=timezone.now() + timedelta(days=3))
        self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            due_date=timezone.now() - timedelta(days=5),
        )

        view_role, stats, _ = get_my_tasks_context(self.designer)
        self.assertEqual(view_role, 'designer')
        self.assertEqual(stats['active_projects'], 2)
        self.assertEqual(stats['running_designs'], 2)
        self.assertEqual(stats['overdue_designs'], 1)
        self.assertEqual(stats['finished_designs'], 1)

    def test_verifier_stats_use_verification_due_date(self):
        on_time = self._create_design(
            self.project_a,
            status=DesignStatus.VERIFICATION_PENDING,
            assigned_verifier=self.verifier,
            verification_due_date=timezone.now() + timedelta(days=2),
        )
        overdue = self._create_design(
            self.project_b,
            status=DesignStatus.VERIFICATION_PENDING,
            assigned_verifier=self.verifier,
            verification_due_date=timezone.now() - timedelta(hours=2),
        )
        finished = self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            assigned_verifier=self.verifier,
            verified_by=self.verifier,
        )

        view_role, stats, querysets = get_my_tasks_context(self.verifier)
        self.assertEqual(view_role, 'verification')
        self.assertEqual(stats['active_projects'], 2)
        self.assertEqual(stats['running_designs'], 2)
        self.assertEqual(stats['overdue_designs'], 1)
        self.assertEqual(stats['finished_designs'], 1)
        self.assertIn(on_time, querysets['active_tasks'])
        self.assertIn(overdue, querysets['active_tasks'])
        self.assertNotIn(finished, querysets['active_tasks'])

    def test_requester_stats_projects_target_overdue_and_finished(self):
        today = timezone.now().date()
        self._create_design(
            self.project_a,
            target_completion_date=today - timedelta(days=2),
        )
        self._create_design(
            self.project_b,
            target_completion_date=today + timedelta(days=5),
        )
        self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            target_completion_date=today - timedelta(days=10),
        )

        view_role, stats, _ = get_my_tasks_context(self.requester)
        self.assertEqual(view_role, 'requester')
        self.assertEqual(stats['projects_requested'], 2)
        self.assertEqual(stats['running_designs'], 2)
        self.assertEqual(stats['target_overdue'], 1)
        self.assertEqual(stats['finished_designs'], 1)

    def test_requester_default_sidebar_includes_my_tasks(self):
        defaults = get_default_sidebar_for_role(UserRole.DESIGN_REQUESTER)
        self.assertTrue(defaults['nav_my_tasks'])
        self.assertTrue(
            PermissionService.has_global_permission(self.requester, 'NAV_PERM_MY_TASKS')
        )
