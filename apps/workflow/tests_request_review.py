from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.models import ActivityLog, UserExtraPermission
from apps.designs.forms import DesignRequestForm, create_design_request
from apps.designs.models import DesignRequest, DesignStatus, DrawingType
from apps.notifications.models import Notification
from apps.permissions.services import PermissionService
from apps.projects.models import Project
from apps.systems.models import SystemGroup, SystemName
from apps.workflow.services import WorkflowError, transition


class RequestUnderReviewWorkflowTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R100',
        )
        self.reviewer = User.objects.create_user(
            username='rev', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='V100',
        )
        self.main_lead = User.objects.create_user(
            username='main', password='pass', role=UserRole.VERIFICATION_TEAM, employee_id='M100',
        )
        self.sub_lead = User.objects.create_user(
            username='sub', password='pass', role=UserRole.COMPLIANCE_TEAM, employee_id='S100',
        )
        UserExtraPermission.objects.create(user=self.main_lead, can_site_engineer=True)
        UserExtraPermission.objects.create(user=self.sub_lead, can_site_engineer=True)
        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H100',
        )
        self.drawing_type = DrawingType.objects.create(
            name='Initial Drawing', code_prefix='ID', allowed_days=3,
        )
        self.project = Project.objects.create(
            name='Test Project', code='PRJ-100', client_name='Client',
            start_date=date.today(), created_by=self.requester,
        )
        self.system_a = SystemName.objects.create(name='Fire Alarm')
        self.system_b = SystemName.objects.create(name='CCTV')
        self.group = SystemGroup.objects.create(
            group_name='Security Systems',
            review_user=self.reviewer,
            is_active=True,
        )
        self.group.systems.set([self.system_a, self.system_b])
        self.other_system = SystemName.objects.create(name='HVAC')
        self.other_group = SystemGroup.objects.create(
            group_name='Mechanical',
            review_user=self.hod,
            is_active=True,
        )
        self.other_group.systems.set([self.other_system])
        self.due = timezone.now() + timedelta(days=5)
        self.client = Client()

    def _create_request(self, requested_by=None):
        return create_design_request(self.project, requested_by or self.requester, {
            'systems': [self.system_a, self.system_b],
            'drawing_type': self.drawing_type,
            'priority': 'medium',
            'target_completion_date': date.today() + timedelta(days=10),
            'request_message': 'Need design',
            'reference_design': None,
        })

    def test_form_rejects_mixed_system_groups(self):
        form = DesignRequestForm(
            data={
                'systems': [self.system_a.pk, self.other_system.pk],
                'drawing_type': self.drawing_type.pk,
                'priority': 'medium',
                'target_completion_date': (date.today() + timedelta(days=10)).isoformat(),
                'request_message': 'Mixed',
            },
            project=self.project,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('systems', form.errors)

    def test_create_routes_to_reviewer(self):
        design = self._create_request()
        self.assertEqual(design.status, DesignStatus.REQUEST_UNDER_REVIEW)
        self.assertEqual(design.assigned_review_user, self.reviewer)
        self.assertEqual(design.current_holder, self.reviewer)
        self.assertEqual(set(design.systems.values_list('pk', flat=True)), {self.system_a.pk, self.system_b.pk})

    def test_reviewer_acknowledge_then_assign(self):
        design = self._create_request()
        transition(design, 'review_acknowledge', self.reviewer)
        design.refresh_from_db()
        self.assertIsNotNone(design.review_acknowledged_at)

        transition(
            design, 'review_assign', self.reviewer,
            main_design_lead=self.main_lead,
            sub_design_lead=self.sub_lead,
            due_date=self.due,
            instructions='Check site layout',
        )
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.ENGINEER_PENDING_ACK)
        self.assertEqual(design.main_design_lead, self.main_lead)
        self.assertEqual(design.sub_design_lead, self.sub_lead)
        self.assertEqual(design.current_holder, self.main_lead)

    def test_review_assign_requires_acknowledge(self):
        design = self._create_request()
        with self.assertRaises(WorkflowError):
            transition(
                design, 'review_assign', self.reviewer,
                main_design_lead=self.main_lead,
                due_date=self.due,
            )

    def test_review_assign_rejects_same_main_and_sub(self):
        design = self._create_request()
        transition(design, 'review_acknowledge', self.reviewer)
        with self.assertRaises(WorkflowError):
            transition(
                design, 'review_assign', self.reviewer,
                main_design_lead=self.main_lead,
                sub_design_lead=self.main_lead,
                due_date=self.due,
            )

    def test_review_assign_form_excludes_selected_leads_from_opposite_dropdown(self):
        from apps.workflow.views import ReviewLeadAssignForm

        design = self._create_request()
        form = ReviewLeadAssignForm(
            data={
                'main_design_lead': str(self.main_lead.pk),
                'sub_design_lead': '',
            },
            design=design,
        )
        sub_ids = set(form.fields['sub_design_lead'].queryset.values_list('pk', flat=True))
        self.assertNotIn(self.main_lead.pk, sub_ids)
        self.assertIn(self.sub_lead.pk, sub_ids)

        form = ReviewLeadAssignForm(
            data={
                'main_design_lead': '',
                'sub_design_lead': str(self.sub_lead.pk),
            },
            design=design,
        )
        main_ids = set(form.fields['main_design_lead'].queryset.values_list('pk', flat=True))
        self.assertNotIn(self.sub_lead.pk, main_ids)
        self.assertIn(self.main_lead.pk, main_ids)

    def test_review_cancel_requires_reason(self):
        design = self._create_request()
        with self.assertRaises(WorkflowError):
            transition(design, 'review_cancel', self.reviewer, comments='  ')

    def test_review_cancel_notifies_requester_with_reason(self):
        design = self._create_request()
        transition(design, 'review_cancel', self.reviewer, comments='Incomplete scope')
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.CANCELLED)
        self.assertEqual(design.review_cancel_reason, 'Incomplete scope')
        self.assertEqual(design.cancel_reason, 'Incomplete scope')
        self.assertTrue(
            Notification.objects.filter(
                user=self.requester,
                title__contains='Cancelled',
                message__contains='Incomplete scope',
            ).exists()
        )

    def test_either_lead_can_acknowledge_and_submit(self):
        design = self._create_request()
        transition(design, 'review_acknowledge', self.reviewer)
        transition(
            design, 'review_assign', self.reviewer,
            main_design_lead=self.main_lead,
            sub_design_lead=self.sub_lead,
            due_date=self.due,
        )
        design.refresh_from_db()
        transition(design, 'acknowledge_engineer', self.sub_lead)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.ENGINEER_IN_PROGRESS)
        transition(design, 'submit_engineer_review', self.main_lead, comments='Site ready')
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.NEW_REQUEST)

    def test_reviewer_visibility(self):
        design = self._create_request()
        visible = PermissionService.filter_design_requests(
            self.reviewer, DesignRequest.objects.all(),
        )
        self.assertIn(design, visible)

    def test_audit_log_for_review_cancel(self):
        design = self._create_request()
        transition(design, 'review_cancel', self.reviewer, comments='Not feasible')
        self.assertTrue(
            ActivityLog.objects.filter(
                entity_type='design_request',
                entity_id=design.pk,
                action='review_cancel',
            ).exists()
        )

    def test_lifecycle_card_reflects_review_cancel(self):
        from apps.designs.lifecycle_timeline import build_lifecycle_data

        design = self._create_request()
        transition(design, 'review_cancel', self.reviewer, comments='Incomplete scope')
        design.refresh_from_db()

        lifecycle = build_lifecycle_data(design)
        self.assertTrue(lifecycle['is_cancelled'])
        self.assertEqual(lifecycle['current_stage_label'], 'Cancelled')
        self.assertEqual(lifecycle['cancel_reason'], 'Incomplete scope')
        self.assertIn(self.reviewer.get_full_name() or self.reviewer.username, lifecycle['cancelled_by_display'])
        reviewer_segments = [
            seg for seg in lifecycle['segments']
            if seg.get('role') == 'reviewer'
        ]
        self.assertEqual(len(reviewer_segments), 1)
        self.assertFalse(reviewer_segments[0]['is_ongoing'])
        self.assertIsNotNone(reviewer_segments[0]['days'])
        self.assertEqual(lifecycle['segments'][-1]['label'], 'Cancelled')

    def test_lifecycle_shows_both_design_leads_when_assigned(self):
        from apps.designs.lifecycle_timeline import build_lifecycle_data

        design = self._create_request()
        transition(design, 'review_acknowledge', self.reviewer)
        transition(
            design, 'review_assign', self.reviewer,
            main_design_lead=self.main_lead,
            sub_design_lead=self.sub_lead,
            due_date=self.due,
        )
        design.refresh_from_db()
        lifecycle = build_lifecycle_data(design)
        self.assertEqual(len(lifecycle['progress_assigned_leads']), 2)
        self.assertIsNotNone(lifecycle['progress_assigned_since_display'])
        role_labels = [lead['role_label'] for lead in lifecycle['progress_assigned_leads']]
        self.assertIn('Main Design Lead', role_labels)
        self.assertIn('Sub Design Lead', role_labels)

    def test_requester_can_cancel_before_review_acknowledge(self):
        from apps.designs.lifecycle_timeline import build_lifecycle_data
        from apps.designs.progress import build_progress_steps
        from apps.workflow.permissions import design_action_flags

        design = self._create_request()
        flags = design_action_flags(self.requester, design)
        self.assertTrue(flags['can_cancel_request'])

        self.client.login(username='req', password='pass')
        response = self.client.post(
            reverse('requests:cancel', kwargs={'pk': design.pk}),
            {'comments': 'Submitted by mistake'},
        )
        self.assertEqual(response.status_code, 302)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.CANCELLED)
        self.assertEqual(design.cancel_reason, 'Submitted by mistake')
        self.assertIsNotNone(design.review_cancelled_at)

        steps, progress_cancelled = build_progress_steps(design)
        self.assertTrue(progress_cancelled)
        lifecycle = build_lifecycle_data(design)
        self.assertTrue(lifecycle['is_cancelled'])
        self.assertEqual(lifecycle['cancel_reason'], 'Submitted by mistake')
        self.assertIn(self.requester.get_full_name() or self.requester.username, lifecycle['cancelled_by_display'])
        self.assertFalse(any(seg.get('is_ongoing') for seg in lifecycle['segments']))
        self.assertTrue(
            Notification.objects.filter(
                user=self.reviewer,
                title__contains='Cancelled',
                message__contains='Submitted by mistake',
            ).exists()
        )

    def test_requester_cancel_requires_reason(self):
        design = self._create_request()
        self.client.login(username='req', password='pass')
        response = self.client.post(
            reverse('requests:cancel', kwargs={'pk': design.pk}),
            {'comments': '   '},
        )
        self.assertEqual(response.status_code, 200)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.REQUEST_UNDER_REVIEW)

    def test_requester_cannot_cancel_after_review_acknowledge(self):
        from apps.workflow.permissions import design_action_flags

        design = self._create_request()
        transition(design, 'review_acknowledge', self.reviewer)
        design.refresh_from_db()
        flags = design_action_flags(self.requester, design)
        self.assertFalse(flags['can_cancel_request'])

        self.client.login(username='req', password='pass')
        response = self.client.post(
            reverse('requests:cancel', kwargs={'pk': design.pk}),
            {'comments': 'Should not work'},
        )
        self.assertEqual(response.status_code, 302)
        design.refresh_from_db()
        self.assertEqual(design.status, DesignStatus.REQUEST_UNDER_REVIEW)

    def test_requester_cannot_cancel_after_review_assign_even_as_sub_lead(self):
        from apps.workflow.permissions import design_action_flags

        design = self._create_request(requested_by=self.sub_lead)
        transition(design, 'review_acknowledge', self.reviewer)
        transition(
            design, 'review_assign', self.reviewer,
            main_design_lead=self.main_lead,
            sub_design_lead=self.sub_lead,
            due_date=self.due,
        )
        design.refresh_from_db()
        flags = design_action_flags(self.sub_lead, design)
        self.assertFalse(flags['can_cancel_request'])
        flags = design_action_flags(self.main_lead, design)
        self.assertFalse(flags['can_cancel_request'])
