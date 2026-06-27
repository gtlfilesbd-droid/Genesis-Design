from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.analytics.reports_display import (
    build_executive_context,
    build_leaderboard_context,
    build_workload_context,
)
from apps.analytics.views import (
    compute_leaderboard_kpis,
    detect_bottlenecks,
    get_leaderboard,
)
from apps.core.settings_forms import ensure_role_permissions
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project, ProjectStatus


class WorkloadDisplayTests(TestCase):
    def test_build_workload_context_summary(self):
        designers = [
            SimpleNamespace(pk=1, workload=0, overdue=0),
            SimpleNamespace(pk=2, workload=6, overdue=1),
            SimpleNamespace(pk=3, workload=3, overdue=0),
        ]
        context = build_workload_context(designers)

        labels = [item['label'] for item in context['summary']]
        self.assertIn('Active tasks', labels)
        self.assertIn('Designers', labels)
        self.assertEqual(context['summary'][1]['value'], 9)

        max_bar = max(row['bar_percent'] for row in context['rows'])
        self.assertLessEqual(max_bar, 100)
        self.assertTrue(any(row['is_suggested'] for row in context['rows']))
        self.assertTrue(any(row['bar_percent'] == 100 for row in context['rows']))


class LeaderboardDisplayTests(TestCase):
    def test_build_leaderboard_context_podium(self):
        user1 = SimpleNamespace(get_full_name=lambda: 'Alice')
        user2 = SimpleNamespace(get_full_name=lambda: 'Bob')
        user3 = SimpleNamespace(get_full_name=lambda: 'Carol')
        user4 = SimpleNamespace(get_full_name=lambda: 'Dan')
        rankings = [
            {'user': user1, 'score': 92.0, 'kpis': {
                'completion_rate': 95, 'on_time_rate': 90, 'first_time_approval_rate': 88,
                'total_corrections': 0, 'total_completed': 10,
            }},
            {'user': user2, 'score': 75.0, 'kpis': {
                'completion_rate': 80, 'on_time_rate': 70, 'first_time_approval_rate': 72,
                'total_corrections': 2, 'total_completed': 8,
            }},
            {'user': user3, 'score': 60.0, 'kpis': {
                'completion_rate': 65, 'on_time_rate': 55, 'first_time_approval_rate': 58,
                'total_corrections': 0, 'total_completed': 5,
            }},
            {'user': user4, 'score': 40.0, 'kpis': {
                'completion_rate': 45, 'on_time_rate': 35, 'first_time_approval_rate': 38,
                'total_corrections': 1, 'total_completed': 3,
            }},
        ]
        context = build_leaderboard_context(rankings, period='monthly')

        self.assertEqual(len(context['podium']), 3)
        self.assertEqual(context['podium'][0]['rank'], 1)
        self.assertEqual(context['summary']['top_score'], 92.0)
        self.assertEqual(context['rows'][0]['score_color'], '#3B6D11')
        self.assertTrue(context['rows'][1]['has_corrections'])


class ExecutiveDisplayTests(TestCase):
    def test_build_executive_context_structures_bottlenecks(self):
        project = SimpleNamespace(code='P1', client_name='Client')
        raw = {
            'total_projects': 2,
            'total_drawings': 10,
            'pending_drawings': 4,
            'overdue_drawings': 1,
            'completion_rate': 60.0,
            'on_track_rate': 75.0,
            'portfolio_health': 82.0,
            'at_risk_projects': 1,
            'active_projects': [SimpleNamespace(
                code='P1', client_name='Client', display_health=42,
            )],
            'top_performers': [{'user': SimpleNamespace(get_full_name=lambda: 'A'), 'score': 88}],
            'bottlenecks': {
                'slow_designers': [{'user': SimpleNamespace(get_full_name=lambda: 'D'), 'overdue_count': 3}],
                'slow_verifiers': [],
                'slow_compliance': [],
                'stalled_projects': [{'project': project, 'health': 40}],
            },
            'design_team_count': 3,
            'verification_team_count': 2,
        }
        context = build_executive_context(raw)

        self.assertEqual(len(context['summary']), 6)
        self.assertEqual(len(context['bottleneck_cards']), 4)
        self.assertEqual(len(context['high_risk_projects']), 1)
        self.assertEqual(context['critical_projects'][0]['health'], 42)
        self.assertEqual(len(context['risk_summary']), 3)
        self.assertEqual(len(context['team_chips']), 3)

    def test_build_executive_context_splits_risk_tiers(self):
        raw = {
            'total_projects': 3,
            'total_drawings': 0,
            'pending_drawings': 0,
            'overdue_drawings': 0,
            'completion_rate': 0,
            'on_track_rate': 100,
            'portfolio_health': 60,
            'at_risk_projects': 2,
            'active_projects': [
                SimpleNamespace(code='HIGH', client_name='A', display_health=45),
                SimpleNamespace(code='MOD', client_name='B', display_health=60),
                SimpleNamespace(code='OK', client_name='C', display_health=80),
            ],
            'top_performers': [],
            'bottlenecks': {
                'slow_designers': [], 'slow_verifiers': [], 'slow_compliance': [], 'stalled_projects': [],
            },
            'design_team_count': 2,
            'verification_team_count': 1,
        }
        context = build_executive_context(raw)

        self.assertEqual(len(context['high_risk_projects']), 1)
        self.assertEqual(context['high_risk_projects'][0]['project'].code, 'HIGH')
        self.assertEqual(context['high_risk_projects'][0]['health_label'], 'Critical')
        self.assertEqual(len(context['moderate_risk_projects']), 1)
        self.assertEqual(context['moderate_risk_projects'][0]['project'].code, 'MOD')
        self.assertEqual(context['moderate_risk_projects'][0]['health_label'], 'At risk')

    def test_executive_context_has_four_bottleneck_cards(self):
        raw = {
            'total_projects': 0,
            'total_drawings': 0,
            'pending_drawings': 0,
            'overdue_drawings': 0,
            'completion_rate': 0,
            'on_track_rate': 0,
            'portfolio_health': 0,
            'at_risk_projects': 0,
            'active_projects': [],
            'top_performers': [],
            'bottlenecks': {
                'slow_designers': [],
                'slow_verifiers': [],
                'slow_compliance': [
                    {'user': SimpleNamespace(get_full_name=lambda: 'Compliance Officer'), 'pending_count': 2},
                ],
                'stalled_projects': [],
            },
            'design_team_count': 0,
            'verification_team_count': 0,
        }
        context = build_executive_context(raw)
        titles = [card['title'] for card in context['bottleneck_cards']]
        self.assertIn('Slow compliance', titles)
        self.assertEqual(len(context['bottleneck_cards']), 4)


class BottleneckDetectionTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.compliance = User.objects.create_user(
            username='cmp', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='C1',
        )
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_detect_bottlenecks_includes_slow_compliance(self):
        from django.utils import timezone

        design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_compliance_officer=self.compliance,
            current_holder=self.compliance,
            status=DesignStatus.COMPLIANCE_PENDING,
        )
        DesignRequest.objects.filter(pk=design.pk).update(
            updated_at=timezone.now() - timedelta(days=4),
        )

        bottlenecks = detect_bottlenecks()

        self.assertEqual(len(bottlenecks['slow_compliance']), 1)
        self.assertEqual(bottlenecks['slow_compliance'][0]['user'], self.compliance)
        self.assertEqual(bottlenecks['slow_compliance'][0]['pending_count'], 1)


class ExecutiveHealthViewTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.project = Project.objects.create(
            name='Active', code='ACT1', client_name='Client',
            start_date=date.today(), created_by=self.requester,
            status=ProjectStatus.ACTIVE,
        )

    @patch('apps.projects.models.Project.save')
    def test_executive_health_not_required_for_display(self, mock_save):
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('analytics:executive'))
        self.assertEqual(response.status_code, 200)
        mock_save.assert_not_called()
        self.assertContains(response, 'Portfolio health')
        self.assertContains(response, 'Bottleneck detection')

    def test_executive_risk_panel_renders_tiers(self):
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('analytics:executive'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'High risk')
        self.assertContains(response, 'Moderate risk')
        self.assertContains(response, 'At risk')
        self.assertContains(response, 'On-track rate')


class ReportsViewTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        )
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C',
            start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_workload_view_renders_for_hod(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=self.designer,
            status=DesignStatus.IN_PROGRESS,
        )
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('analytics:workload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team capacity')
        self.assertContains(response, 'Active tasks')
        self.assertContains(response, 'Suggested next')

    def test_leaderboard_view_renders(self):
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('analytics:leaderboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full rankings')
        self.assertNotContains(response, '🥇')
        self.assertNotContains(response, '🥈')
        self.assertNotContains(response, '🥉')

    def test_leaderboard_period_query_param(self):
        self.client.login(username='hod', password='pass')
        response = self.client.get(reverse('analytics:leaderboard'), {'period': 'yearly'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yearly')
        self.assertContains(response, 'Rankings include designers with 3+ completions')


class LeaderboardFairnessTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='reqlb', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='RL1',
        )
        self.hod = User.objects.create_user(
            username='hodlb', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='HL1',
        )
        self.busy = User.objects.create_user(
            username='busy', password='pass', role=UserRole.DESIGNER, employee_id='BL1',
        )
        self.light = User.objects.create_user(
            username='light', password='pass', role=UserRole.DESIGNER, employee_id='LL1',
        )
        self.project = Project.objects.create(
            name='P', code='PLB', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def _create_completed(self, designer, when=None):
        from django.utils import timezone
        from apps.designs.models import DesignAssignment

        when = when or timezone.now()
        design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=designer,
            status=DesignStatus.COMPLETED,
            completion_date=when,
            due_date=when + timedelta(days=1),
        )
        DesignAssignment.objects.create(
            design=design, designer=designer, assigned_by=self.hod,
        )
        return design

    def test_leaderboard_excludes_low_volume(self):
        for _ in range(2):
            self._create_completed(self.busy)
        data = get_leaderboard('monthly')
        ranked_ids = [r['user'].pk for r in data['rankings']]
        self.assertNotIn(self.busy.pk, ranked_ids)
        self.assertGreaterEqual(data['excluded_count'], 1)

    def test_leaderboard_busy_designer_qualifies_in_period(self):
        from django.utils import timezone

        now = timezone.now()
        for _ in range(12):
            self._create_completed(self.busy, when=now)
        for _ in range(8):
            design = DesignRequest.objects.create(
                project=self.project,
                drawing_type=self.drawing_type,
                requested_by=self.requester,
                assigned_designer=self.busy,
                status=DesignStatus.IN_PROGRESS,
            )
            from apps.designs.models import DesignAssignment
            DesignAssignment.objects.create(
                design=design, designer=self.busy, assigned_by=self.hod,
            )
        for _ in range(3):
            self._create_completed(self.light, when=now)

        busy_kpis = compute_leaderboard_kpis(self.busy, 'monthly')
        self.assertEqual(busy_kpis['total_completed'], 12)
        self.assertEqual(busy_kpis['total_assigned'], 20)

        data = get_leaderboard('monthly')
        ranked_ids = [r['user'].pk for r in data['rankings']]
        self.assertIn(self.busy.pk, ranked_ids)
        self.assertIn(self.light.pk, ranked_ids)

    def test_leaderboard_monthly_filters_old_completions(self):
        from django.utils import timezone

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        old = month_start - timedelta(days=5)
        self._create_completed(self.busy, when=old)
        kpis = compute_leaderboard_kpis(self.busy, 'monthly')
        self.assertEqual(kpis['total_completed'], 0)


class WorkloadHodTests(TestCase):
    def setUp(self):
        ensure_role_permissions()
        self.client = Client()
        self.hod = User.objects.create_user(
            username='hod2', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H2',
        )
        self.requester = User.objects.create_user(
            username='req2', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R2',
        )
        self.project = Project.objects.create(
            name='P', code='P2', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_workload_includes_hod(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=self.hod,
            status=DesignStatus.IN_PROGRESS,
        )
        self.client.login(username='hod2', password='pass')
        response = self.client.get(reverse('analytics:workload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hod.get_full_name())
