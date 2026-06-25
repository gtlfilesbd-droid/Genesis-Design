from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.designs.lifecycle_timeline import (
    _format_days_count,
    build_lifecycle_data,
    build_timeline_segments,
    format_completed_target_on_time_summary,
    format_delay_target_summary,
    format_person_display,
    get_current_delay_info,
    get_hod_name_and_id,
    get_lifecycle_timeline_data,
)
from apps.designs.models import DesignAssignment, DesignRequest, DesignStatus, DrawingType
from apps.projects.models import Project
from apps.workflow.services import transition


class LifecycleTimelineTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req',
            password='pass',
            role=UserRole.DESIGN_REQUESTER,
            employee_id='R001',
        )
        self.hod = User.objects.create_user(
            username='hod',
            password='pass',
            role=UserRole.HEAD_OF_DESIGN,
            employee_id='H001',
            first_name='Head',
            last_name='Design',
        )
        self.designer = User.objects.create_user(
            username='designer1',
            password='pass',
            role=UserRole.DESIGNER,
            employee_id='D001',
            first_name='Rahim',
            last_name='Designer',
        )
        self.project = Project.objects.create(
            name='Test Project',
            code='TST',
            client_name='Test Client',
            start_date=date.today(),
            created_by=self.requester,
        )
        self.drawing_type = DrawingType.objects.create(
            name='Floor Plan',
            code_prefix='FP',
            allowed_days=5,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.NEW_REQUEST,
            target_completion_date=date.today() + timedelta(days=10),
        )

    def test_new_request_shows_awaiting_ack_and_pending_chain(self):
        data = build_lifecycle_data(self.design)
        self.assertIsNotNone(data)
        labels = [s['label'] for s in data['segments']]
        self.assertIn('Acknowledgement', labels)

    def test_build_lifecycle_data_stats(self):
        data = build_lifecycle_data(self.design)
        self.assertIsNotNone(data['total_days'])
        self.assertEqual(data['current_stage_label'], 'Acknowledgement')

    def test_unacknowledged_delay_info_points_to_hod(self):
        self.design.target_completion_date = date.today() - timedelta(days=1)
        self.design.save(update_fields=['target_completion_date'])
        delay = get_current_delay_info(self.design)
        self.assertIsNotNone(delay)
        self.assertIn('Acknowledgement', delay['current_stage_label'])
        self.assertTrue(delay['is_overdue'])

    def test_acknowledge_assign_designer_flow(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=3),
        )
        transition(self.design, 'accept_assignment', self.designer)

        segments = build_timeline_segments(self.design)
        labels = [s['label'] for s in segments if not s.get('is_pending')]
        self.assertTrue(any('Assign' in label or 'Designer' in label for label in labels))

    def test_correction_creates_multiple_designer_segments(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=3),
        )
        transition(self.design, 'accept_assignment', self.designer)
        transition(self.design, 'submit_work', self.designer, comments='V1')
        transition(self.design, 'request_correction', self.hod, comments='Fix')
        transition(self.design, 'resubmit', self.designer, comments='V2')

        segments = build_timeline_segments(self.design)
        designer_labels = [s['label'] for s in segments if s['role'] == 'designer' and not s.get('is_pending')]
        self.assertGreaterEqual(len(designer_labels), +2)

    def test_completed_on_time_shows_green_status(self):
        transition(self.design, 'acknowledge', self.hod)
        self.design.target_completion_date = date.today() + timedelta(days=30)
        self.design.completion_date = timezone.now()
        self.design.status = DesignStatus.COMPLETED
        self.design.save()

        data = get_lifecycle_timeline_data(self.design)
        self.assertTrue(data['is_completed_on_time'])
        self.assertIsNone(data['delay_info'])

    def test_admin_user_not_shown_when_hod_exists(self):
        admin = User.objects.create_user(
            username='admin',
            password='pass',
            role=UserRole.ADMIN,
            employee_id='A001',
            first_name='Admin',
            last_name='User',
            is_superuser=True,
        )
        self.assertIsNotNone(admin)

        data = build_lifecycle_data(self.design)
        people_names = [p['name'] for p in data['people']]
        self.assertNotIn('Admin User', people_names)
        self.assertNotIn('Admin User', data.get('current_person_display', '') or '')
        self.assertNotIn('Admin User', data.get('delay_person_display', '') or '')

        hod_name, hod_id = get_hod_name_and_id(self.design)
        self.assertEqual(hod_name, 'Head Design')
        self.assertEqual(hod_id, self.hod.id)

    def test_overdue_new_request_shows_hod_not_admin(self):
        User.objects.create_user(
            username='admin',
            password='pass',
            role=UserRole.ADMIN,
            employee_id='A002',
            first_name='Admin',
            last_name='User',
            is_superuser=True,
        )
        self.design.target_completion_date = date.today() - timedelta(days=1)
        self.design.save(update_fields=['target_completion_date'])

        data = build_lifecycle_data(self.design)
        self.assertTrue(data['is_overdue'])
        self.assertNotIn('Admin User', data['delay_person_display'])
        self.assertIn('Head of Design', data['delay_person_display'])
        self.assertIsNotNone(data['delay_waiting_days'])
        self.assertGreaterEqual(data['delay_waiting_days'], 0)
        if data['delay_waiting_days']:
            self.assertTrue(data['delay_waiting_days_display'].startswith('('))

    def test_acknowledged_request_shows_hod_name_with_role(self):
        transition(self.design, 'acknowledge', self.hod)

        data = build_lifecycle_data(self.design)
        expected = format_person_display('Head Design', 'Head of Design')
        ack_segments = [s for s in data['segments'] if s['label'] == 'Acknowledgement']
        self.assertTrue(any(s['person'] == 'Head Design' for s in ack_segments))
        people_names = [p['display_name'] for p in data['people']]
        self.assertIn(expected, people_names)

    def test_delay_info_resolves_hod_not_admin(self):
        User.objects.create_user(
            username='admin',
            password='pass',
            role=UserRole.ADMIN,
            employee_id='A003',
            first_name='Admin',
            last_name='User',
        )
        self.design.target_completion_date = date.today() - timedelta(days=1)
        self.design.save(update_fields=['target_completion_date'])

        delay = get_current_delay_info(self.design)
        self.assertIsNotNone(delay)
        self.assertNotEqual(delay['current_person'], 'Admin User')
        self.assertEqual(delay['person_id'], self.hod.id)

    def test_overdue_compliance_ack_delay_banner_fields(self):
        compliance = User.objects.create_user(
            username='nadia',
            password='pass',
            role=UserRole.COMPLIANCE_TEAM,
            employee_id='C001',
            first_name='Nadia',
            last_name='Compliance',
        )
        self.design.status = DesignStatus.COMPLIANCE_PENDING_ACK
        self.design.deadline_start = timezone.now() - timedelta(days=10)
        self.design.assigned_compliance_officer = compliance
        self.design.compliance_assigned_at = timezone.now() - timedelta(days=2)
        self.design.target_completion_date = date.today() - timedelta(days=1)
        self.design.save()
        DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.hod,
            assigned_at=timezone.now() - timedelta(days=9),
        )

        data = build_lifecycle_data(self.design)
        self.assertTrue(data['is_overdue'])
        self.assertEqual(data['delay_stage_role'], 'Compliance')
        self.assertEqual(data['delay_stage_step'], 'Acknowledgement')
        self.assertEqual(data['delay_waiting_on'], 'Nadia Compliance')
        self.assertNotIn('(Compliance)', data['delay_waiting_on'])
        self.assertIsNotNone(data['delay_waiting_days'])
        self.assertGreater(data['delay_waiting_days'], 0)
        self.assertEqual(data['delay_waiting_days_display'], _format_days_count(data['delay_waiting_days']))
        self.assertIn('deadline', data['delay_target_summary'])
        self.assertIn('(', data['delay_target_summary'])
        self.assertIn('day', data['delay_target_summary'])

        expected_summary = format_delay_target_summary(
            data['days_over_target'],
            self.design.target_completion_date,
        )
        self.assertEqual(data['delay_target_summary'], expected_summary)

    def test_designer_waiting_days_independent_of_request_past_target(self):
        transition(self.design, 'acknowledge', self.hod)
        hod_due = timezone.now() + timedelta(days=30)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=hod_due,
        )
        transition(self.design, 'accept_assignment', self.designer)

        self.design.target_completion_date = date.today() - timedelta(days=5)
        self.design.save(update_fields=['target_completion_date'])

        assignment = self.design.assignments.order_by('-assigned_at').first()
        assigned_at = timezone.now() - timedelta(days=3)
        DesignAssignment.objects.filter(pk=assignment.pk).update(assigned_at=assigned_at)

        data = build_lifecycle_data(self.design)
        self.assertTrue(data['is_overdue'])
        self.assertGreater(data['days_over_target'], 0)
        self.assertIsNotNone(data['delay_waiting_days'])
        self.assertGreater(data['delay_waiting_days'], 0)
        self.assertNotEqual(data['delay_waiting_days'], data['days_over_target'])
        self.assertEqual(data['delay_waiting_on'], 'Rahim Designer')

        requester_deadline = self.design.target_completion_date.strftime('%d %b %Y')
        self.assertIn(requester_deadline, data['delay_target_summary'])
        hod_due_str = hod_due.strftime('%d %b %Y')
        self.assertNotIn(hod_due_str, data['delay_target_summary'])

        waiting_since = data['delay_since']
        self.assertIsNotNone(waiting_since)
        self.assertAlmostEqual(
            data['delay_waiting_days'],
            (timezone.now() - waiting_since).total_seconds() / 86400,
            delta=0.2,
        )

    def test_in_progress_ack_shows_hod_name_before_acknowledge(self):
        data = build_lifecycle_data(self.design)
        self.assertEqual(data['current_stage_label'], 'Acknowledgement')
        self.assertIn('Head Design', data['progress_assigned_summary'])
        self.assertIn('(Head of Design)', data['progress_assigned_summary'])

    def test_in_progress_banner_uses_name_role_and_target_summary(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=30),
        )
        transition(self.design, 'accept_assignment', self.designer)
        self.design.target_completion_date = date.today() + timedelta(days=10)
        self.design.save(update_fields=['target_completion_date'])

        data = build_lifecycle_data(self.design)
        self.assertFalse(data['is_overdue'])
        self.assertIn('(Designer)', data['progress_assigned_summary'])
        self.assertIn('since', data['progress_assigned_summary'])
        self.assertIn('deadline', data['progress_target_summary'])
        self.assertIn('left', data['progress_target_summary'])

    def test_completed_on_time_banner_stacked_summaries(self):
        transition(self.design, 'acknowledge', self.hod)
        self.design.target_completion_date = date.today() + timedelta(days=30)
        self.design.completion_date = timezone.now()
        self.design.status = DesignStatus.COMPLETED
        self.design.save()

        data = build_lifecycle_data(self.design)
        self.assertTrue(data['is_completed_on_time'])
        self.assertIn('Finished', data['completed_finished_summary'])
        self.assertEqual(
            data['completed_target_summary'],
            format_completed_target_on_time_summary(self.design.target_completion_date),
        )

    def test_completed_late_banner_uses_past_target_format(self):
        transition(self.design, 'acknowledge', self.hod)
        transition(
            self.design,
            'assign',
            self.hod,
            designer=self.designer,
            due_date=timezone.now() + timedelta(days=3),
        )
        transition(self.design, 'accept_assignment', self.designer)
        self.design.target_completion_date = date.today() - timedelta(days=4)
        self.design.completion_date = timezone.now()
        self.design.status = DesignStatus.COMPLETED
        self.design.save()

        data = build_lifecycle_data(self.design)
        self.assertFalse(data['is_completed_on_time'])
        self.assertIn('deadline', data['completed_late_target_summary'])
        self.assertIn('(', data['completed_late_target_summary'])
        expected = format_delay_target_summary(
            data['days_late'],
            self.design.target_completion_date,
        )
        self.assertEqual(data['completed_late_target_summary'], expected)
