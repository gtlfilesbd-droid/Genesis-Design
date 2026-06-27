from datetime import date
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
            'critical_projects': [SimpleNamespace(
                code='P1', client_name='Client', display_health=42,
            )],
            'top_performers': [{'user': SimpleNamespace(get_full_name=lambda: 'A'), 'score': 88}],
            'bottlenecks': {
                'slow_designers': [{'user': SimpleNamespace(get_full_name=lambda: 'D'), 'overdue_count': 3}],
                'slow_verifiers': [],
                'stalled_projects': [{'project': project, 'health': 40}],
            },
            'design_team_count': 3,
            'verification_team_count': 2,
        }
        context = build_executive_context(raw)

        self.assertEqual(len(context['summary']), 6)
        self.assertEqual(len(context['bottleneck_cards']), 3)
        self.assertEqual(context['critical_projects'][0]['health'], 42)


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
