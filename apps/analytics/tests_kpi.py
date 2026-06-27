from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.analytics.kpi_display import build_kpi_page_context
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
        self.assertEqual(context['headline']['label'], 'Completion Rate')
        self.assertEqual(len(context['sections']), 2)
        labels = [card['label'] for section in context['sections'] for card in section['cards']]
        self.assertIn('Total Requests', labels)
        self.assertIn('Completion Rate', labels)
        self.assertNotIn('total_requests', labels)

    def test_build_kpi_page_context_designer_includes_rate_cards(self):
        kpis = compute_designer_kpis(User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        ))
        context = build_kpi_page_context(UserRole.DESIGNER, kpis)

        self.assertTrue(context['has_kpis'])
        rate_cards = [
            card for section in context['sections'] for card in section['cards']
            if card['type'] == 'rate'
        ]
        self.assertGreaterEqual(len(rate_cards), 3)
        self.assertEqual(rate_cards[0]['label'], 'On-Time Rate')
        self.assertIn('tone_class', rate_cards[0])

    def test_build_kpi_page_context_empty_for_admin(self):
        context = build_kpi_page_context(UserRole.ADMIN, {})
        self.assertFalse(context['has_kpis'])
        self.assertIsNone(context['headline'])
