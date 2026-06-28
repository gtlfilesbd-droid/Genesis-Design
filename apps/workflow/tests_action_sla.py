from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.models import DeadlineConfiguration
from apps.designs.models import (
    ComplianceReview,
    DesignAssignment,
    DesignRequest,
    DesignStatus,
    DesignSubmission,
    DrawingType,
    Verification,
)
from apps.projects.models import Project
from apps.workflow.action_sla import (
    get_action_due_at,
    is_action_overdue,
    is_action_overdue_for_user,
)


class ActionSlaTests(TestCase):
    def setUp(self):
        from apps.accounts.models import User, UserRole

        self.hod = User.objects.create_user(
            username='hod', password='pass', role=UserRole.HEAD_OF_DESIGN, employee_id='H1',
        )
        self.designer = User.objects.create_user(
            username='des', password='pass', role=UserRole.DESIGNER, employee_id='D1',
        )
        self.drawing_type = DrawingType.objects.create(name='Layout', code_prefix='LY', allowed_days=3)
        self.requester = User.objects.create_user(
            username='req', password='pass', role=UserRole.DESIGN_REQUESTER, employee_id='R1',
        )
        self.project = Project.objects.create(
            name='P', code='P1', client_name='Client', start_date=timezone.now().date(),
            created_by=self.requester,
        )
        self.design = DesignRequest.objects.create(
            project=self.project,
            drawing_type=self.drawing_type,
            requested_by=self.requester,
            status=DesignStatus.NEW_REQUEST,
            current_holder=self.hod,
        )
        config = DeadlineConfiguration.get_solo()
        config.action_acknowledge_days = 1
        config.action_acknowledge_hours = 0
        config.save()

    def test_new_request_action_due_from_config(self):
        DesignRequest.objects.filter(pk=self.design.pk).update(
            created_at=timezone.now() - timedelta(hours=2),
        )
        self.design.refresh_from_db()
        due = get_action_due_at(self.design)
        self.assertIsNotNone(due)
        self.assertGreater(due, self.design.created_at)

    def test_new_request_overdue_after_sla(self):
        DesignRequest.objects.filter(pk=self.design.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        self.design.refresh_from_db()
        self.assertTrue(is_action_overdue(self.design))
        self.assertTrue(is_action_overdue_for_user(self.design, self.hod))

    def test_assigned_accept_sla(self):
        self.design.status = DesignStatus.ASSIGNED
        self.design.assigned_designer = self.designer
        self.design.save()
        assignment = DesignAssignment.objects.create(
            design=self.design,
            designer=self.designer,
            assigned_by=self.hod,
        )
        DesignAssignment.objects.filter(pk=assignment.pk).update(
            assigned_at=timezone.now() - timedelta(days=2),
        )
        self.assertTrue(is_action_overdue_for_user(self.design, self.designer))

    def test_hod_review_sla_uses_submission_anchor(self):
        self.design.status = DesignStatus.UNDER_REVIEW
        self.design.current_holder = self.hod
        self.design.save()
        DesignSubmission.objects.create(
            design=self.design,
            version_number=1,
            file_name='test.pdf',
            revision_date=timezone.now().date(),
            internal_file_reference='ref',
            submitted_by=self.designer,
        )
        config = DeadlineConfiguration.get_solo()
        config.action_hod_review_days = 2
        config.save()
        submission = self.design.submissions.first()
        DesignSubmission.objects.filter(pk=submission.pk).update(
            submitted_at=timezone.now() - timedelta(days=3),
        )
        self.design.refresh_from_db()
        self.assertTrue(is_action_overdue_for_user(self.design, self.hod))

    def test_approved_mark_complete_sla(self):
        self.design.status = DesignStatus.APPROVED
        self.design.current_holder = self.hod
        self.design.save()
        ComplianceReview.objects.create(
            design=self.design,
            reviewer=self.hod,
            action='approved',
        )
        review = self.design.compliance_reviews.first()
        ComplianceReview.objects.filter(pk=review.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        self.design.refresh_from_db()
        self.assertTrue(is_action_overdue_for_user(self.design, self.hod))
