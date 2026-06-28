from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.accounts.sidebar_permissions import get_default_sidebar_for_role
from apps.core.models import DeadlineConfiguration
from apps.core.dashboard_helpers import get_dashboard_stats
from apps.core.my_tasks_helpers import (
    build_my_tasks_request_url,
    filter_my_tasks_stat,
    get_my_tasks_context,
    get_my_tasks_stat_cards,
)
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import (
    ComplianceReview,
    DesignAssignment,
    DesignRequest,
    DesignStatus,
    DrawingType,
)
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
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.compliance = User.objects.create_user(
            username='comp', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='C1',
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
            completion_date=timezone.now() - timedelta(days=5),
            due_date=timezone.now() - timedelta(days=5),
        )

        view_role, period, stats, _ = get_my_tasks_context(self.designer)
        self.assertEqual(view_role, 'designer')
        self.assertEqual(period, 'all')
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

        view_role, _, stats, querysets = get_my_tasks_context(self.verifier)
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
            completion_date=timezone.now() - timedelta(days=10),
            target_completion_date=today - timedelta(days=10),
        )

        view_role, _, stats, _ = get_my_tasks_context(self.requester)
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

    def test_hod_stats_involvement_and_overdue(self):
        ack = self._create_design(
            self.project_a,
            status=DesignStatus.NEW_REQUEST,
            assigned_designer=None,
            current_holder=self.hod,
            target_completion_date=timezone.now().date() - timedelta(days=1),
        )
        DesignRequest.objects.filter(pk=ack.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        ack.refresh_from_db()
        self_work = self._create_design(
            self.project_b,
            status=DesignStatus.IN_PROGRESS,
            assigned_designer=self.hod,
            current_holder=self.hod,
            assigned_by=self.hod,
            due_date=timezone.now() - timedelta(hours=1),
        )
        self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            completion_date=timezone.now() - timedelta(days=2),
            assigned_by=self.hod,
            assigned_designer=self.designer,
        )

        view_role, _, stats, querysets = get_my_tasks_context(self.hod)
        self.assertEqual(view_role, 'hod')
        self.assertEqual(stats['active_projects'], 2)
        self.assertEqual(stats['running_designs'], 2)
        self.assertEqual(stats['overdue_designs'], 2)
        self.assertEqual(stats['finished_designs'], 1)
        self.assertIn(ack, querysets['active_tasks'])
        self.assertIn(self_work, querysets['active_tasks'])

    def test_hod_excludes_verification_stage_from_active_and_overdue(self):
        at_verification = self._create_design(
            self.project_a,
            status=DesignStatus.VERIFICATION_PENDING,
            assigned_designer=self.hod,
            assigned_verifier=self.verifier,
            current_holder=self.verifier,
            due_date=timezone.now() - timedelta(days=2),
        )
        _, _, stats, querysets = get_my_tasks_context(self.hod)
        self.assertEqual(stats['running_designs'], 0)
        self.assertEqual(stats['overdue_designs'], 0)
        self.assertNotIn(at_verification, querysets['active_tasks'])

    def test_designer_excludes_verification_stage_from_active_and_overdue(self):
        at_verification = self._create_design(
            self.project_a,
            status=DesignStatus.VERIFICATION_PENDING,
            assigned_designer=self.designer,
            assigned_verifier=self.verifier,
            current_holder=self.verifier,
            due_date=timezone.now() - timedelta(days=2),
        )
        _, _, stats, querysets = get_my_tasks_context(self.designer)
        self.assertEqual(stats['running_designs'], 0)
        self.assertEqual(stats['overdue_designs'], 0)
        self.assertNotIn(at_verification, querysets['assigned_tasks'])

    def test_hod_overdue_filter_excludes_verification_stage_design(self):
        at_verification = self._create_design(
            self.project_a,
            status=DesignStatus.VERIFICATION_PENDING,
            assigned_designer=self.hod,
            assigned_verifier=self.verifier,
            current_holder=self.verifier,
            due_date=timezone.now() - timedelta(days=2),
        )
        overdue_ack = self._create_design(
            self.project_b,
            status=DesignStatus.NEW_REQUEST,
            assigned_designer=None,
            current_holder=self.hod,
            target_completion_date=timezone.now().date() - timedelta(days=1),
        )
        DesignRequest.objects.filter(pk=overdue_ack.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        overdue_ack.refresh_from_db()
        qs = DesignRequest.objects.all()
        filtered = filter_my_tasks_stat(qs, self.hod, 'hod', 'overdue')
        self.assertIn(overdue_ack, filtered)
        self.assertNotIn(at_verification, filtered)

        self.client.login(username='hod', password='pass')
        url = build_my_tasks_request_url('hod', 'overdue')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, overdue_ack.design_number)
        self.assertNotContains(response, at_verification.design_number)

    def test_hod_ack_action_sla_overdue_not_target_date(self):
        target_only = self._create_design(
            self.project_a,
            status=DesignStatus.NEW_REQUEST,
            assigned_designer=None,
            current_holder=self.hod,
            target_completion_date=timezone.now().date() - timedelta(days=5),
        )
        ack_overdue = self._create_design(
            self.project_b,
            status=DesignStatus.NEW_REQUEST,
            assigned_designer=None,
            current_holder=self.hod,
        )
        DesignRequest.objects.filter(pk=ack_overdue.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        filtered = filter_my_tasks_stat(DesignRequest.objects.all(), self.hod, 'hod', 'overdue')
        self.assertNotIn(target_only, filtered)
        self.assertIn(ack_overdue, filtered)

    def test_designer_assigned_action_sla_overdue(self):
        assigned = self._create_design(
            self.project_a,
            status=DesignStatus.ASSIGNED,
            assigned_designer=self.designer,
        )
        assignment = DesignAssignment.objects.create(
            design=assigned,
            designer=self.designer,
            assigned_by=self.hod,
        )
        DesignAssignment.objects.filter(pk=assignment.pk).update(
            assigned_at=timezone.now() - timedelta(days=2),
        )
        _, _, stats, _ = get_my_tasks_context(self.designer)
        self.assertEqual(stats['overdue_designs'], 1)

    def test_hod_dashboard_overdue_uses_pipeline_scope(self):
        ack_overdue = self._create_design(
            self.project_a,
            status=DesignStatus.NEW_REQUEST,
            assigned_designer=None,
            current_holder=self.hod,
        )
        DesignRequest.objects.filter(pk=ack_overdue.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        designer_overdue = self._create_design(
            self.project_b,
            status=DesignStatus.IN_PROGRESS,
            assigned_designer=self.designer,
            current_holder=self.designer,
            assigned_by=self.hod,
            due_date=timezone.now() - timedelta(days=1),
        )
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('accounts:hod_dashboard'))
        self.assertEqual(response.status_code, 200)
        _, _, mt_stats, _ = get_my_tasks_context(self.hod)
        pipeline_stats = get_dashboard_stats(self.hod)
        self.assertEqual(mt_stats['overdue_designs'], 1)
        self.assertEqual(pipeline_stats['overdue_designs'], 1)
        self.assertEqual(
            response.context['stats']['overdue_designs'],
            pipeline_stats['overdue_designs'],
        )
        filtered_pipeline = filter_my_tasks_stat(
            DesignRequest.objects.filter(due_date__lt=timezone.now()).exclude(
                status__in=[DesignStatus.COMPLETED, DesignStatus.CANCELLED],
            ),
            self.hod,
            'hod',
            'overdue',
        )
        self.assertIn(designer_overdue, DesignRequest.objects.filter(due_date__lt=timezone.now()))
        self.assertNotIn(ack_overdue, DesignRequest.objects.filter(due_date__lt=timezone.now()))
        self.assertNotIn(designer_overdue, filtered_pipeline)
        self.assertIn('overdue=1', response.context['dashboard_overdue_url'])
        self.assertNotIn('scope=hod', response.context['dashboard_overdue_url'])

    def test_period_filter_scopes_finished_not_running(self):
        old_completed = self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            completion_date=timezone.now() - timedelta(days=40),
            due_date=timezone.now() - timedelta(days=40),
        )
        recent_completed = self._create_design(
            self.project_b,
            status=DesignStatus.COMPLETED,
            completion_date=timezone.now() - timedelta(days=2),
            due_date=timezone.now() - timedelta(days=2),
        )
        self._create_design(
            self.project_a,
            due_date=timezone.now() + timedelta(days=3),
        )

        _, _, stats_all, _ = get_my_tasks_context(self.designer, period='all')
        _, _, stats_week, _ = get_my_tasks_context(self.designer, period='week')

        self.assertEqual(stats_all['finished_designs'], 2)
        self.assertEqual(stats_week['finished_designs'], 1)
        self.assertEqual(stats_all['running_designs'], stats_week['running_designs'])
        self.assertIn(old_completed.design_number, DesignRequest.objects.values_list('design_number', flat=True))
        self.assertIn(recent_completed.design_number, DesignRequest.objects.values_list('design_number', flat=True))

    def test_requester_period_scopes_projects_requested(self):
        old = self._create_design(
            self.project_a,
            created_at=timezone.now() - timedelta(days=60),
        )
        DesignRequest.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=60))
        recent = self._create_design(self.project_b)

        _, _, stats_all, _ = get_my_tasks_context(self.requester, period='all')
        _, _, stats_month, _ = get_my_tasks_context(self.requester, period='month')

        self.assertEqual(stats_all['projects_requested'], 2)
        self.assertEqual(stats_month['projects_requested'], 1)
        self.assertEqual(recent.project_id, self.project_b.pk)

    def test_stat_cards_link_to_design_requests_with_scope_and_stat(self):
        _, _, stats, _ = get_my_tasks_context(self.designer, period='month')
        cards = get_my_tasks_stat_cards('designer', stats, period='month')
        self.assertEqual(len(cards), 4)
        running = next(c for c in cards if c['key'] == 'running')
        self.assertIn('scope=designer', running['url'])
        self.assertIn('stat=running', running['url'])
        self.assertIn('period=month', running['url'])

    def test_filter_my_tasks_stat_matches_running_count(self):
        self._create_design(self.project_a, due_date=timezone.now() + timedelta(days=2))
        self._create_design(self.project_b, due_date=timezone.now() + timedelta(days=3))
        self._create_design(
            self.project_a,
            status=DesignStatus.COMPLETED,
            completion_date=timezone.now(),
        )
        qs = DesignRequest.objects.all()
        filtered = filter_my_tasks_stat(qs, self.designer, 'designer', 'running')
        self.assertEqual(filtered.count(), 2)

    def test_design_request_list_scoped_filter(self):
        self.client.login(username='des', password='pass')
        running = self._create_design(self.project_a, due_date=timezone.now() + timedelta(days=2))
        self._create_design(
            self.project_b,
            status=DesignStatus.COMPLETED,
            completion_date=timezone.now(),
        )
        url = build_my_tasks_request_url('designer', 'running')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, running.design_number)
        self.assertNotContains(response, 'Completed this month')
