from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.analytics.views import compute_compliance_kpis, compute_requester_kpis
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

    def test_compute_requester_kpis_counts_projects_and_requests(self):
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

        Project.objects.create(
            name='Done', code='P2', client_name='C2',
            start_date=date.today(), created_by=self.requester,
            status=ProjectStatus.COMPLETED,
        )

        kpis = compute_requester_kpis(self.requester)

        self.assertEqual(kpis['total_projects'], 2)
        self.assertEqual(kpis['active_projects'], 1)
        self.assertEqual(kpis['completed_projects'], 1)
        self.assertEqual(kpis['total_requests'], 2)
        self.assertEqual(kpis['pending_requests'], 1)
        self.assertEqual(kpis['completed_requests'], 1)
        self.assertEqual(kpis['completion_rate'], 50.0)
