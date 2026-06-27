from datetime import date

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.analytics.views import compute_compliance_kpis
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project


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
