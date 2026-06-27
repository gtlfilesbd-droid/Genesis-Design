from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.analytics.kpi_display import TONE_COLORS, _build_headline, build_kpi_page_context
from apps.analytics.views import compute_compliance_kpis, compute_designer_kpis, compute_requester_kpis
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project, ProjectStatus


class ComplianceKpiTests(TestCase):
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

    def test_compute_compliance_kpis_counts_assigned_reviews(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_compliance_officer=self.compliance,
            status=DesignStatus.COMPLIANCE_PENDING,
        )
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            approved_by_compliance=self.compliance,
            status=DesignStatus.APPROVED,
        )

        kpis = compute_compliance_kpis(self.compliance)

        self.assertEqual(kpis['total_reviewed'], 2)
        self.assertEqual(kpis['approved'], 1)


class RequesterKpiTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.project = Project.objects.create(
            name='P', code='P1', client_name='C',
            start_date=date.today(), created_by=self.requester,
            status=ProjectStatus.ACTIVE,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_compute_requester_kpis_counts_requests(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.NEW_REQUEST,
        )
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.COMPLETED,
        )

        kpis = compute_requester_kpis(self.requester)

        self.assertEqual(kpis['total_requests'], 2)
        self.assertEqual(kpis['pending_requests'], 1)
        self.assertEqual(kpis['completed_requests'], 1)
        self.assertEqual(kpis['completion_rate'], 50.0)
        self.assertNotIn('total_projects', kpis)


class KpiDisplayTests(TestCase):
    def test_build_kpi_page_context_requester_has_sections(self):
        kpis = {
            'total_requests': 4,
            'completed_requests': 2,
            'pending_requests': 2,
            'completion_rate': 50.0,
        }
        context = build_kpi_page_context(UserRole.DESIGN_REQUESTER, kpis)

        self.assertTrue(context['has_kpis'])
        self.assertEqual(context['headline']['label'], 'Completion rate')
        self.assertEqual(len(context['sections']), 2)
        labels = [card['label'] for section in context['sections'] for card in section['cards']]
        self.assertIn('Total requests', labels)
        self.assertIn('Completion rate', labels)
        self.assertNotIn('total_requests', labels)

    def test_build_kpi_page_context_designer_includes_rate_cards(self):
        kpis = compute_designer_kpis(User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        ))
        context = build_kpi_page_context(UserRole.DESIGNER, kpis)

        self.assertTrue(context['has_kpis'])
        rate_section = next(s for s in context['sections'] if s['type'] == 'rate')
        rate_labels = [card['label'] for card in rate_section['cards']]
        self.assertGreaterEqual(len(rate_labels), 3)
        self.assertEqual(rate_labels[0], 'On-time rate')
        self.assertIn('value_color', rate_section['cards'][0])
        self.assertNotIn('Completion rate', rate_labels)

    def test_build_kpi_page_context_designer_avg_completion_card(self):
        kpis = {
            'total_assigned': 10,
            'total_completed': 8,
            'total_corrections': 2,
            'on_time_rate': 80.0,
            'late_rate': 20.0,
            'first_time_approval_rate': 70.0,
            'completion_rate': 80.0,
            'avg_completion_days': 4.2,
        }
        context = build_kpi_page_context(UserRole.DESIGNER, kpis)
        rate_labels = [
            card['label'] for section in context['sections']
            if section['type'] == 'rate' for card in section['cards']
        ]
        self.assertIn('Avg. completion time', rate_labels)
        avg_card = next(
            card for section in context['sections'] for card in section['cards']
            if card.get('label') == 'Avg. completion time'
        )
        self.assertEqual(avg_card['unit'], 'd')
        self.assertEqual(avg_card['value'], 4.2)

    def test_build_kpi_page_context_empty_for_admin(self):
        context = build_kpi_page_context(UserRole.ADMIN, {})
        self.assertFalse(context['has_kpis'])
        self.assertIsNone(context['headline'])

    def test_build_headline_ring_offset_calculation(self):
        headline = _build_headline('Completion rate', 87, 'test context')
        self.assertAlmostEqual(headline['ring_offset'], 251.3 - (251.3 * 87 / 100), places=1)

    def test_build_headline_inverted_tone_for_overdue_rate(self):
        headline = _build_headline('Overdue rate', 15, 'test context', inverted=True)
        self.assertEqual(headline['value_color'], TONE_COLORS['good']['text'])