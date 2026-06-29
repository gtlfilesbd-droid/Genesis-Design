from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.analytics.kpi_display import TONE_COLORS, _build_headline, build_kpi_page_context
from apps.analytics.views import (
    compute_compliance_kpis,
    compute_designer_kpis,
    compute_hod_kpis,
    compute_requester_kpis,
    compute_verification_kpis,
)
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

    def test_compute_compliance_kpis_includes_pending(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_compliance_officer=self.compliance,
            status=DesignStatus.COMPLIANCE_PENDING,
        )

        kpis = compute_compliance_kpis(self.compliance)

        self.assertEqual(kpis['pending'], 1)
        self.assertIn('avg_review_hours', kpis)


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

    def test_compute_requester_kpis_includes_status_counts(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.CANCELLED,
        )

        kpis = compute_requester_kpis(self.requester)

        self.assertEqual(kpis['cancelled_requests'], 1)
        self.assertIn('overdue_rate', kpis)
        self.assertIn('in_progress', kpis)


class DesignerKpiComputeTests(TestCase):
    def setUp(self):
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
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

    def test_compute_designer_kpis_includes_workload_metrics(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=self.designer,
            status=DesignStatus.IN_PROGRESS,
        )

        kpis = compute_designer_kpis(self.designer)

        self.assertEqual(kpis['in_progress'], 1)
        self.assertIn('monthly_output', kpis)
        self.assertIn('yearly_output', kpis)
        self.assertIn('fastest_days', kpis)


class HodKpiComputeTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req3', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R3',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.project = Project.objects.create(
            name='P', code='P3', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_compute_hod_kpis_includes_pipeline_counts(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.UNDER_REVIEW,
        )
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.IN_PROGRESS,
        )

        kpis = compute_hod_kpis(self.hod)

        self.assertEqual(kpis['waiting_review'], 1)
        self.assertEqual(kpis['with_designer'], 1)
        self.assertIn('approval_rate', kpis)
        self.assertIn('active_pipeline', kpis)

    def test_hod_kpi_includes_personal_design_metrics(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_designer=self.hod,
            status=DesignStatus.IN_PROGRESS,
        )
        team_kpis = compute_hod_kpis(self.hod)
        personal = compute_designer_kpis(self.hod)
        kpis = {**team_kpis, **{f'my_{k}': v for k, v in personal.items()}}

        self.assertEqual(kpis['my_total_assigned'], 1)
        self.assertIn('my_in_progress', kpis)
        self.assertIn('active_pipeline', kpis)

    def test_hod_kpi_page_shows_my_design_work_section(self):
        team_kpis = compute_hod_kpis(self.hod)
        personal = compute_designer_kpis(self.hod)
        kpis = {**team_kpis, **{f'my_{k}': v for k, v in personal.items()}}
        context = build_kpi_page_context(UserRole.HEAD_OF_DESIGN, kpis)

        section_titles = [section['label'] for section in context['sections']]
        self.assertIn('My design work', section_titles)
        self.assertIn('Volume', section_titles)


class VerificationKpiComputeTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req4', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R4',
        )
        self.verifier = User.objects.create_user(
            username='ver', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='V1',
        )
        self.project = Project.objects.create(
            name='P', code='P4', client_name='C', start_date=date.today(), created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )

    def test_compute_verification_kpis_includes_pending(self):
        DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            assigned_verifier=self.verifier,
            status=DesignStatus.VERIFICATION_PENDING,
        )

        kpis = compute_verification_kpis(self.verifier)

        self.assertEqual(kpis['pending'], 1)
        self.assertIn('corrections_sent', kpis)
        self.assertIn('avg_verification_hours', kpis)


class KpiDisplayTests(TestCase):
    def test_build_kpi_page_context_requester_has_sections(self):
        kpis = {
            'total_requests': 4,
            'completed_requests': 2,
            'in_progress': 2,
            'pending_requests': 2,
            'cancelled_requests': 0,
            'overdue_requests': 0,
            'completion_rate': 50.0,
            'overdue_rate': 0.0,
        }
        context = build_kpi_page_context(UserRole.DESIGN_REQUESTER, kpis)

        self.assertTrue(context['has_kpis'])
        self.assertEqual(context['headline']['label'], 'Completion rate')
        self.assertGreaterEqual(len(context['sections']), 2)
        labels = [card['label'] for section in context['sections'] for card in section['cards']]
        self.assertIn('Total requests', labels)
        self.assertIn('Overdue rate', labels)
        self.assertNotIn('total_requests', labels)

    def test_build_kpi_page_context_requester_no_duplicate_completion_rate(self):
        kpis = {
            'total_requests': 4,
            'completed_requests': 2,
            'in_progress': 2,
            'pending_requests': 2,
            'cancelled_requests': 0,
            'overdue_requests': 1,
            'completion_rate': 50.0,
            'overdue_rate': 50.0,
        }
        context = build_kpi_page_context(UserRole.DESIGN_REQUESTER, kpis)
        rate_labels = [
            card['label'] for section in context['sections']
            if section['type'] == 'rate' for card in section['cards']
        ]
        self.assertNotIn('Completion rate', rate_labels)
        self.assertIn('Overdue rate', rate_labels)

    def test_build_kpi_page_context_designer_includes_rate_cards(self):
        kpis = compute_designer_kpis(User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        ))
        context = build_kpi_page_context(UserRole.DESIGNER, kpis)

        self.assertTrue(context['has_kpis'])
        section_labels = [section['label'] for section in context['sections']]
        self.assertIn('Workload', section_labels)
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
            'in_progress': 1,
            'overdue': 0,
            'monthly_output': 3,
            'yearly_output': 8,
            'on_time_rate': 80.0,
            'late_rate': 20.0,
            'first_time_approval_rate': 70.0,
            'completion_rate': 80.0,
            'avg_completion_days': 4.2,
            'fastest_days': 2.0,
            'slowest_days': 7.0,
        }
        context = build_kpi_page_context(UserRole.DESIGNER, kpis)
        rate_labels = [
            card['label'] for section in context['sections']
            if section['type'] == 'rate' for card in section['cards']
        ]
        self.assertIn('Avg. completion time', rate_labels)
        self.assertIn('Fastest completion', rate_labels)
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

    def test_kpi_alert_only_on_overdue_stat_cards(self):
        kpis = {
            'total_requests': 10,
            'completed_requests': 4,
            'in_progress': 5,
            'pending_requests': 1,
            'cancelled_requests': 0,
            'overdue_requests': 3,
            'overdue_rate': 20.0,
            'completion_rate': 40.0,
        }
        context = build_kpi_page_context(UserRole.DESIGN_REQUESTER, kpis)
        stat_cards = [
            card for section in context['sections']
            for card in section['cards']
            if 'is_danger' in card
        ]
        overdue_card = next(c for c in stat_cards if c['label'] == 'Overdue')
        self.assertTrue(overdue_card['is_kpi_alert'])
        self.assertTrue(overdue_card['is_danger'])

        verifier_kpis = {
            'total_verified': 8,
            'approved': 5,
            'pending': 3,
            'corrections_sent': 4,
            'accuracy_rate': 75.0,
            'correction_rate': 25.0,
            'avg_verification_hours': 2.5,
        }
        verifier_context = build_kpi_page_context(UserRole.VERIFICATION_TEAM, verifier_kpis)
        verifier_cards = [
            card for section in verifier_context['sections']
            for card in section['cards']
            if 'is_danger' in card
        ]
        corrections_card = next(c for c in verifier_cards if 'Correction' in c['label'])
        self.assertFalse(corrections_card.get('is_kpi_alert'))
        self.assertTrue(corrections_card['is_danger'])
