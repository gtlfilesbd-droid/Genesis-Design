from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.models import UserExtraPermission
from apps.core.utils import log_activity
from apps.designs.forms import create_design_request
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project
from apps.reports.audit_report import build_workflow_audit_report, get_audit_report_for_design_number
from apps.workflow.services import transition


class WorkflowAuditReportTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R001',
            first_name='Request', last_name='User',
        )
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H001',
            first_name='Head', last_name='Design',
        )
        self.engineer = User.objects.create_user(
            username='eng', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='E001',
            first_name='Site', last_name='Engineer',
        )
        UserExtraPermission.objects.create(user=self.engineer, can_site_engineer=True)
        self.admin = User.objects.create_user(
            username='admin', password='pass', role=UserRole.ADMIN, employee_id='A001',
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.project = Project.objects.create(
            name='Colosia', code='Colosia', client_name='Client',
            start_date=date.today(), created_by=self.requester,
        )
        self.due = timezone.now() + timedelta(days=5)
        self.design = create_design_request(self.project, self.requester, {
            'drawing_type': self.drawing_type,
            'priority': 'medium',
            'target_completion_date': date.today() + timedelta(days=10),
            'request_message': 'Need site check',
            'reference_design': None,
            'assigned_site_engineer': self.engineer,
            'engineer_due_date': self.due,
            'engineer_instructions': 'Measure all rooms',
        })

    def test_build_report_includes_request_metadata(self):
        report = build_workflow_audit_report(self.design)
        self.assertEqual(report['design_number'], self.design.design_number)
        self.assertEqual(report['requested_by'], 'Request User')
        self.assertEqual(report['project_code'], 'Colosia')
        self.assertTrue(report['rows'])

    def test_build_report_chronological_stages(self):
        transition(self.design, 'acknowledge_engineer', self.engineer)
        transition(
            self.design, 'submit_engineer_review', self.engineer,
            comments='Site measurements complete',
        )
        transition(self.design, 'acknowledge', self.hod)
        self.design.refresh_from_db()

        report = build_workflow_audit_report(self.design)
        stages = [row['stage'] for row in report['rows']]
        self.assertIn('Request Submitted', stages)
        self.assertIn('Site engineer acknowledged', stages)
        self.assertIn('Site review submitted', stages)
        self.assertIn('Request acknowledged', stages)

        timestamps = [row['timestamp'] for row in report['rows'] if row['timestamp']]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_lookup_by_design_number_case_insensitive(self):
        report = get_audit_report_for_design_number(self.design.design_number.lower())
        self.assertIsNotNone(report)
        self.assertEqual(report['design_number'], self.design.design_number)

    def test_action_sla_delay_marked_on_late_acknowledge(self):
        self.design.engineer_assigned_at = timezone.now() - timedelta(days=5)
        self.design.save(update_fields=['engineer_assigned_at'])
        transition(self.design, 'acknowledge_engineer', self.engineer)
        self.design.refresh_from_db()

        report = build_workflow_audit_report(self.design)
        ack_rows = [r for r in report['rows'] if r.get('action') == 'acknowledge_engineer']
        self.assertEqual(len(ack_rows), 1)
        self.assertTrue(ack_rows[0]['is_delayed'])
        self.assertEqual(ack_rows[0]['delay_type'], 'action_sla')
        self.assertEqual(ack_rows[0]['delayed_by'], 'Site Engineer')

    def test_primary_delay_source_marked(self):
        self.design.delay_source = 'Site Engineer'
        self.design.delay_duration_days = 3
        self.design.save(update_fields=['delay_source', 'delay_duration_days'])
        log_activity(
            'design_request', self.design.pk, self.engineer, 'acknowledge_engineer',
            'Site Engineer acknowledged',
            {'old_status': DesignStatus.ENGINEER_PENDING_ACK, 'new_status': DesignStatus.ENGINEER_IN_PROGRESS},
        )

        report = build_workflow_audit_report(self.design)
        self.assertIsNotNone(report['delay_summary'])
        delayed_rows = [r for r in report['rows'] if r['is_delayed'] and r['delay_type'] == 'primary_delay']
        self.assertTrue(delayed_rows)

    def test_reports_audit_tab_requires_permission(self):
        self.client.login(username='req', password='pass')
        response = self.client.get(reverse('reports:index'), {'tab': 'audit', 'design': self.design.design_number})
        self.assertEqual(response.status_code, 302)

    def test_reports_audit_tab_shows_report_for_admin(self):
        self.client.login(username='admin', password='pass')
        response = self.client.get(reverse('reports:index'), {'tab': 'audit', 'design': self.design.design_number})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.design.design_number)
        self.assertContains(response, 'Workflow Audit')

    def test_csv_export_design_workflow_audit(self):
        self.client.login(username='admin', password='pass')
        url = reverse('reports:export_csv', args=['design_workflow_audit'])
        response = self.client.get(url, {'design': self.design.design_number})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.design.design_number, content)
        self.assertIn('Stage', content)
        self.assertIn('Delayed By', content)
