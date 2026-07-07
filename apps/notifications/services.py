from django.contrib.auth import get_user_model

from django.conf import settings
from django.core.mail import send_mail

from apps.core.notification_messages import (
    acknowledged_message,
    assignment_accepted_message,
    compliance_acknowledged_message,
    compliance_approved_message,
    compliance_correction_message,
    correction_required_message,
    design_accepted_message,
    design_approved_message,
    design_completed_message,
    design_leads_assigned_message,
    design_leads_assigned_requester_message,
    designer_assigned_message,
    designer_assigned_requester_message,
    hod_fast_complete_message,
    request_created_message,
    request_review_acknowledged_message,
    request_review_cancelled_message,
    request_cancelled_by_requester_message,
    request_sent_for_review_message,
    sent_to_compliance_message,
    sent_to_compliance_requester_message,
    sent_to_verification_message,
    verification_acknowledged_message,
    verification_approved_message,
    verification_correction_message,
    work_submitted_message,
)
from apps.permissions.services import PermissionService

from .models import Notification, NotificationSetting, NotificationType

User = get_user_model()


def create_notification(user, title, message, link='', notification_type=NotificationType.WORKFLOW):
    if not user:
        return
    if not getattr(user, 'is_active', True):
        return
    config = NotificationSetting.get_solo()
    if config.enable_in_app:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            link=link,
            notification_type=notification_type,
        )
    if config.enable_email and user.email:
        send_mail(
            subject=f'[Genesis Design] {title}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )


class NotificationService:
    @staticmethod
    def notify(recipient, notif_type, title, message, related_request=None, link=''):
        if not recipient:
            return
        if related_request and not link:
            link = f'/requests/{related_request.pk}/'
        create_notification(recipient, title, message, link, notif_type)

    @staticmethod
    def _notify_many(users, notif_type, title, message, related_request=None):
        seen = set()
        for user in users:
            if user and user.pk not in seen:
                seen.add(user.pk)
                NotificationService.notify(
                    user, notif_type, title, message, related_request=related_request,
                )

    @staticmethod
    def _project_users(project, permission_code):
        return [
            user for user in User.objects.filter(is_active=True, status='active')
            if PermissionService.has_project_permission(user, project, permission_code)
        ]

    @staticmethod
    def _requester_side_recipients(design_request):
        """Submitting requester and project owner (when different)."""
        recipients = []
        seen = set()
        project = design_request.project
        for user in (design_request.requested_by, getattr(project, 'created_by', None)):
            if user and user.pk not in seen:
                seen.add(user.pk)
                recipients.append(user)
        return recipients

    @staticmethod
    def _merge_recipients(*user_lists, exclude=None):
        """Dedupe users from one or more lists, optionally excluding an actor."""
        recipients = []
        seen = set()
        exclude_pk = exclude.pk if exclude else None
        for user_list in user_lists:
            if not user_list:
                continue
            iterable = user_list if isinstance(user_list, (list, tuple)) else [user_list]
            for user in iterable:
                if not user:
                    continue
                if exclude_pk and user.pk == exclude_pk:
                    continue
                if user.pk not in seen:
                    seen.add(user.pk)
                    recipients.append(user)
        return recipients

    @staticmethod
    def on_request_created(design_request):
        users = NotificationService._project_users(
            design_request.project, 'PROJECT_PERM_ASSIGN',
        )
        title = f'New Design Request: {design_request.design_number}'
        message = request_created_message(design_request)
        NotificationService._notify_many(
            users, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_request_sent_for_review(design_request):
        if not design_request.assigned_review_user_id:
            return
        title = f'Review Required: {design_request.design_number}'
        message = request_sent_for_review_message(design_request)
        NotificationService.notify(
            design_request.assigned_review_user,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_request_review_acknowledged(design_request, actor):
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            exclude=actor,
        )
        title = f'Request Acknowledged: {design_request.design_number}'
        message = request_review_acknowledged_message(
            design_request, actor.get_full_name() or actor.username,
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_request_review_cancelled(design_request):
        recipients = NotificationService._requester_side_recipients(design_request)
        title = f'Request Cancelled: {design_request.design_number}'
        message = request_review_cancelled_message(
            design_request,
            design_request.cancel_reason_display or 'No reason provided',
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_request_cancelled_by_requester(design_request, actor):
        reason = design_request.cancel_reason_display or 'No reason provided'
        requester_name = actor.get_full_name() or actor.username
        recipients = []
        if (
            design_request.assigned_review_user_id
            and design_request.assigned_review_user_id != actor.pk
        ):
            recipients.append(design_request.assigned_review_user)
        if not recipients:
            return
        title = f'Request Cancelled: {design_request.design_number}'
        message = request_cancelled_by_requester_message(
            design_request, requester_name, reason,
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_design_leads_assigned(design_request):
        recipients = []
        if design_request.main_design_lead_id:
            recipients.append(design_request.main_design_lead)
        if design_request.sub_design_lead_id:
            recipients.append(design_request.sub_design_lead)
        for lead in recipients:
            is_sub = design_request.sub_design_lead_id == lead.pk
            title = f'Site Design Lead Assignment: {design_request.design_number}'
            message = design_leads_assigned_message(design_request, is_sub=is_sub)
            NotificationService.notify(
                lead, NotificationType.WORKFLOW, title, message, related_request=design_request,
            )
        requester_title = f'Site Design Leads Assigned: {design_request.design_number}'
        requester_message = design_leads_assigned_requester_message(design_request)
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            requester_title,
            requester_message,
            design_request,
        )

    @staticmethod
    def on_engineer_assigned(design_request):
        title = f'Site Design Lead Assignment: {design_request.design_number}'
        from apps.core.notification_messages import (
            engineer_assigned_message,
            engineer_assigned_requester_message,
        )
        message = engineer_assigned_message(design_request)
        NotificationService.notify(
            design_request.assigned_site_engineer,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )
        requester_title = f'Site Design Lead Assigned: {design_request.design_number}'
        requester_message = engineer_assigned_requester_message(design_request)
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            requester_title,
            requester_message,
            design_request,
        )

    @staticmethod
    def on_engineer_acknowledged(design_request, actor):
        from apps.core.notification_messages import engineer_acknowledged_message
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            exclude=actor,
        )
        title = f'Site Design Lead Acknowledged: {design_request.design_number}'
        message = engineer_acknowledged_message(design_request, actor.get_full_name())
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_engineer_submitted(design_request):
        users = NotificationService._project_users(
            design_request.project, 'PROJECT_PERM_ASSIGN',
        )
        from apps.core.notification_messages import engineer_submitted_message
        title = f'Site Review Submitted: {design_request.design_number}'
        message = engineer_submitted_message(design_request)
        NotificationService._notify_many(
            users, NotificationType.WORKFLOW, title, message, design_request,
        )
        requester_title = f'Site Review Complete: {design_request.design_number}'
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            requester_title,
            message,
            design_request,
        )

    @staticmethod
    def on_request_acknowledged(design_request):
        title = f'Request Acknowledged: {design_request.design_number}'
        hod_name = design_request.current_holder.get_full_name() if design_request.current_holder else 'Head of Design'
        message = acknowledged_message(design_request, hod_name)
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            title,
            message,
            design_request,
        )

    @staticmethod
    def on_designer_assigned(design_request):
        title = f'Assignment: {design_request.design_number}'
        message = designer_assigned_message(design_request)
        NotificationService.notify(
            design_request.assigned_designer,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )
        requester_title = f'Designer Assigned: {design_request.design_number}'
        requester_message = designer_assigned_requester_message(design_request)
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            requester_title,
            requester_message,
            design_request,
        )

    @staticmethod
    def on_assignment_accepted(design_request, actor):
        recipients = NotificationService._merge_recipients(
            NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
            exclude=actor,
        )
        title = f'Assignment Accepted: {design_request.design_number}'
        message = assignment_accepted_message(design_request, actor)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_work_submitted(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_REVIEW',
            ),
            NotificationService._requester_side_recipients(design_request),
        )
        title = f'Work Submitted: {design_request.design_number}'
        message = work_submitted_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_correction_required(design_request):
        title = f'Correction Required: {design_request.design_number}'
        message = correction_required_message(design_request)
        NotificationService.notify(
            design_request.assigned_designer,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_design_accepted(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            [design_request.assigned_designer] if design_request.assigned_designer_id else [],
        )
        title = f'Design Accepted: {design_request.design_number}'
        message = design_accepted_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_sent_to_verification(design_request):
        verifier = design_request.current_holder
        if not verifier:
            verifiers = PermissionService.get_verifiers(design_request.project)
            verifier = verifiers.first()
        title = f'Verification Required: {design_request.design_number}'
        message = sent_to_verification_message(design_request)
        if verifier:
            NotificationService.notify(
                verifier,
                NotificationType.WORKFLOW,
                title,
                message,
                related_request=design_request,
            )
        else:
            NotificationService._notify_many(
                PermissionService.get_verifiers(design_request.project),
                NotificationType.WORKFLOW,
                title,
                message,
                design_request,
            )

    @staticmethod
    def on_verification_correction(design_request):
        from apps.workflow.services import get_head_of_design

        hod = get_head_of_design()
        recipients = NotificationService._merge_recipients(
            [hod] if hod else NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
        )
        title = f'Verification Correction: {design_request.design_number}'
        message = verification_correction_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_verification_approved(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
        )
        title = f'Verification Approved: {design_request.design_number}'
        message = verification_approved_message(
            design_request,
            design_request.verified_by.get_full_name() if design_request.verified_by else 'Verifier',
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_verification_acknowledged(design_request, actor):
        recipients = NotificationService._merge_recipients(
            NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
            exclude=actor,
        )
        title = f'Verification Acknowledged: {design_request.design_number}'
        verifier_name = actor.get_full_name() or actor.username
        message = verification_acknowledged_message(design_request, verifier_name)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_compliance_acknowledged(design_request, actor):
        recipients = NotificationService._merge_recipients(
            NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
            exclude=actor,
        )
        title = f'Compliance Acknowledged: {design_request.design_number}'
        compliance_name = actor.get_full_name() or actor.username
        message = compliance_acknowledged_message(design_request, compliance_name)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_sent_to_compliance(design_request):
        officer = design_request.assigned_compliance_officer or design_request.current_holder
        title = f'Compliance Review Required: {design_request.design_number}'
        message = sent_to_compliance_message(design_request)
        if officer:
            NotificationService.notify(
                officer,
                NotificationType.WORKFLOW,
                title,
                message,
                related_request=design_request,
            )
        else:
            NotificationService._notify_many(
                PermissionService.get_compliance_officers(design_request.project),
                NotificationType.WORKFLOW,
                title,
                message,
                design_request,
            )
        requester_title = f'Sent to Compliance: {design_request.design_number}'
        requester_message = sent_to_compliance_requester_message(design_request)
        NotificationService._notify_many(
            NotificationService._requester_side_recipients(design_request),
            NotificationType.WORKFLOW,
            requester_title,
            requester_message,
            design_request,
        )

    @staticmethod
    def on_compliance_correction(design_request):
        from apps.workflow.services import get_head_of_design

        hod = get_head_of_design()
        recipients = NotificationService._merge_recipients(
            [hod] if hod else NotificationService._project_users(
                design_request.project, 'PROJECT_PERM_ASSIGN',
            ),
            NotificationService._requester_side_recipients(design_request),
        )
        title = f'Compliance Correction: {design_request.design_number}'
        message = compliance_correction_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_compliance_approved(design_request):
        from apps.workflow.services import get_head_of_design

        recipients = NotificationService._merge_recipients(
            [get_head_of_design()],
            NotificationService._requester_side_recipients(design_request),
            [design_request.assigned_designer] if design_request.assigned_designer_id else [],
        )
        title = f'Design Approved: {design_request.design_number}'
        officer_name = (
            design_request.approved_by_compliance.get_full_name()
            if design_request.approved_by_compliance else 'Compliance officer'
        )
        message = compliance_approved_message(design_request, officer_name)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_hod_fast_complete(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            [design_request.assigned_designer] if design_request.assigned_designer_id else [],
        )
        title = f'Design Completed: {design_request.design_number}'
        message = hod_fast_complete_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_approved(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            [design_request.assigned_designer] if design_request.assigned_designer_id else [],
            [design_request.verified_by] if design_request.verified_by_id else [],
        )
        title = f'Design Approved: {design_request.design_number}'
        message = design_approved_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_completed(design_request):
        recipients = NotificationService._merge_recipients(
            NotificationService._requester_side_recipients(design_request),
            [design_request.assigned_designer] if design_request.assigned_designer_id else [],
        )
        title = f'Design Completed: {design_request.design_number}'
        message = design_completed_message(design_request)
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )


def notify_workflow_transition(design, action, actor):
    """Dispatch workflow notifications for a completed transition action."""
    from apps.designs.models import DesignRequest

    design = DesignRequest.objects.select_related(
        'requested_by',
        'assigned_designer',
        'assigned_site_engineer',
        'main_design_lead',
        'sub_design_lead',
        'assigned_review_user',
        'project',
        'project__created_by',
        'assigned_verifier',
        'verified_by',
        'assigned_compliance_officer',
    ).get(pk=design.pk)

    handlers = {
        'submit_request': NotificationService.on_request_created,
        'review_acknowledge': NotificationService.on_request_review_acknowledged,
        'review_assign': NotificationService.on_design_leads_assigned,
        'review_cancel': NotificationService.on_request_review_cancelled,
        'acknowledge': NotificationService.on_request_acknowledged,
        'acknowledge_engineer': NotificationService.on_engineer_acknowledged,
        'submit_engineer_review': NotificationService.on_engineer_submitted,
        'assign': NotificationService.on_designer_assigned,
        'accept_assignment': NotificationService.on_assignment_accepted,
        'submit_work': NotificationService.on_work_submitted,
        'request_correction': NotificationService.on_correction_required,
        'resubmit': NotificationService.on_work_submitted,
        'send_to_verification': _notify_send_to_verification,
        'accept_design': _notify_send_to_verification,
        'verification_correction': NotificationService.on_verification_correction,
        'forward_to_designer': NotificationService.on_correction_required,
        'accept_verification': NotificationService.on_verification_acknowledged,
        'verify_approved': NotificationService.on_verification_approved,
        'send_to_compliance': NotificationService.on_sent_to_compliance,
        'accept_compliance': NotificationService.on_compliance_acknowledged,
        'compliance_correction': NotificationService.on_compliance_correction,
        'compliance_approved': NotificationService.on_compliance_approved,
        'hod_fast_complete': NotificationService.on_hod_fast_complete,
        'complete': NotificationService.on_completed,
    }
    handler = handlers.get(action)
    if handler:
        if action in (
            'accept_assignment', 'accept_verification', 'accept_compliance',
            'acknowledge_engineer', 'review_acknowledge',
        ):
            handler(design, actor)
        else:
            handler(design)


def _notify_send_to_verification(design):
    NotificationService.on_design_accepted(design)
    NotificationService.on_sent_to_verification(design)


def send_escalation(design, level):
    from apps.accounts.models import UserRole

    link = f'/requests/{design.pk}/'
    title = f'Deadline Escalation Level {level}: {design.design_number}'
    message = f'Design {design.design_number} has missed deadline. Escalation level {level}.'

    if level == 1 and design.assigned_designer:
        create_notification(
            design.assigned_designer, title, message, link, NotificationType.ESCALATION
        )
    elif level == 2:
        hod = User.objects.filter(role=UserRole.HEAD_OF_DESIGN, is_active=True).first()
        create_notification(hod, title, message, link, NotificationType.ESCALATION)
    elif level == 3 and design.assigned_designer and design.assigned_designer.manager:
        create_notification(
            design.assigned_designer.manager, title, message, link, NotificationType.ESCALATION
        )
    elif level == 4:
        admins = User.objects.filter(role=UserRole.ADMIN, is_active=True)
        for admin in admins:
            create_notification(admin, title, message, link, NotificationType.ESCALATION)


def notify_action_sla_breach(design):
    from apps.accounts.models import UserRole
    from apps.designs.models import DesignStatus

    link = f'/requests/{design.pk}/'
    due = design.action_due_at
    due_text = due.strftime('%d %b %Y %H:%M') if due else 'N/A'
    title = f'Action Overdue: {design.design_number}'
    message = (
        f'Design {design.design_number} requires your action (due {due_text}). '
        f'Current status: {design.get_status_display()}.'
    )
    recipients = []
    if design.current_holder:
        recipients.append(design.current_holder)
    if design.status == DesignStatus.ASSIGNED and design.assigned_designer:
        recipients = [design.assigned_designer]
    elif design.status == DesignStatus.VERIFICATION_PENDING_ACK and design.assigned_verifier:
        recipients = [design.assigned_verifier]
    elif design.status == DesignStatus.COMPLIANCE_PENDING_ACK and design.assigned_compliance_officer:
        recipients = [design.assigned_compliance_officer]
    hod = User.objects.filter(role=UserRole.HEAD_OF_DESIGN, is_active=True).first()
    if hod and hod not in recipients:
        recipients.append(hod)
    for user in recipients:
        create_notification(user, title, message, link, NotificationType.DEADLINE)


def notify_deadline_breach(design):
    from apps.accounts.models import UserRole

    link = f'/requests/{design.pk}/'
    title = f'Deadline Missed: {design.design_number}'
    due_text = design.deadline_due.strftime('%d %b %Y %H:%M') if design.deadline_due else 'N/A'
    message = (
        f'Design {design.design_number} missed its deadline (due {due_text}). '
        f'Please review and take action.'
    )
    recipients = []
    if design.assigned_designer:
        recipients.append(design.assigned_designer)
    hod = User.objects.filter(role=UserRole.HEAD_OF_DESIGN, is_active=True).first()
    if hod:
        recipients.append(hod)
    for user in recipients:
        create_notification(user, title, message, link, NotificationType.DEADLINE)


def notify_deadline_warning(design):
    from apps.accounts.models import UserRole

    link = f'/requests/{design.pk}/'
    title = f'Deadline Warning: {design.design_number}'
    due_text = design.deadline_due.strftime('%d %b %Y %H:%M') if design.deadline_due else 'N/A'
    message = (
        f'Design {design.design_number} is approaching its deadline (due {due_text}). '
        f'Current status: {design.get_deadline_status_display()}.'
    )
    recipients = []
    if design.assigned_designer:
        recipients.append(design.assigned_designer)
    if design.current_holder and design.current_holder not in recipients:
        recipients.append(design.current_holder)
    hod = User.objects.filter(role=UserRole.HEAD_OF_DESIGN, is_active=True).first()
    if hod and hod not in recipients:
        recipients.append(hod)
    for user in recipients:
        create_notification(user, title, message, link, NotificationType.DEADLINE)
