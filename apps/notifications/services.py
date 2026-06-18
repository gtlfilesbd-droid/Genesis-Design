from django.contrib.auth import get_user_model

from django.conf import settings
from django.core.mail import send_mail

from apps.permissions.services import PermissionService

from .models import Notification, NotificationSetting, NotificationType

User = get_user_model()


def create_notification(user, title, message, link='', notification_type=NotificationType.WORKFLOW):
    if not user:
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
    def on_request_created(design_request):
        users = NotificationService._project_users(
            design_request.project, 'PROJECT_PERM_ASSIGN',
        )
        title = f'New Design Request: {design_request.design_number}'
        message = (
            f'A new design request {design_request.design_number} was submitted '
            f'for project {design_request.project.code}.'
        )
        NotificationService._notify_many(
            users, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_request_acknowledged(design_request):
        title = f'Request Acknowledged: {design_request.design_number}'
        message = (
            f'Your design request {design_request.design_number} has been acknowledged '
            f'and is being processed.'
        )
        NotificationService.notify(
            design_request.requested_by,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_designer_assigned(design_request):
        title = f'Assignment: {design_request.design_number}'
        message = (
            f'You have been assigned to design request {design_request.design_number} '
            f'for project {design_request.project.code}.'
        )
        NotificationService.notify(
            design_request.assigned_designer,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_assignment_accepted(design_request, actor):
        users = NotificationService._project_users(
            design_request.project, 'PROJECT_PERM_ASSIGN',
        )
        recipients = [u for u in users if u and u.pk != actor.pk]
        title = f'Assignment Accepted: {design_request.design_number}'
        message = (
            f'{actor.get_full_name() or actor.username} has accepted the assignment '
            f'for design request {design_request.design_number}.'
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_work_submitted(design_request):
        users = NotificationService._project_users(
            design_request.project, 'PROJECT_PERM_REVIEW',
        )
        title = f'Work Submitted: {design_request.design_number}'
        message = (
            f'Design work has been submitted for {design_request.design_number} '
            f'and is ready for review.'
        )
        NotificationService._notify_many(
            users, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_correction_required(design_request):
        title = f'Correction Required: {design_request.design_number}'
        message = (
            f'Corrections are required on design request {design_request.design_number}. '
            f'Please review the feedback and resubmit.'
        )
        NotificationService.notify(
            design_request.assigned_designer,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_design_accepted(design_request):
        recipients = [
            design_request.requested_by,
            design_request.assigned_designer,
        ]
        title = f'Design Accepted: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has been accepted by review '
            f'and will proceed to verification.'
        )
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
        message = (
            f'Design {design_request.design_number} is pending verification.'
        )
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
        title = f'Verification Correction: {design_request.design_number}'
        message = (
            f'Verification corrections are required for {design_request.design_number}.'
        )
        NotificationService.notify(
            hod,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_verification_approved(design_request):
        from apps.workflow.services import get_head_of_design

        hod = get_head_of_design()
        title = f'Verification Approved: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has passed verification. '
            f'Please assign a compliance officer.'
        )
        NotificationService.notify(
            hod,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_sent_to_compliance(design_request):
        officer = design_request.assigned_compliance_officer or design_request.current_holder
        title = f'Compliance Review Required: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} is pending compliance review.'
        )
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

    @staticmethod
    def on_compliance_correction(design_request):
        from apps.workflow.services import get_head_of_design

        hod = get_head_of_design()
        title = f'Compliance Correction: {design_request.design_number}'
        message = (
            f'Compliance corrections are required for {design_request.design_number}.'
        )
        NotificationService.notify(
            hod,
            NotificationType.WORKFLOW,
            title,
            message,
            related_request=design_request,
        )

    @staticmethod
    def on_compliance_approved(design_request):
        from apps.workflow.services import get_head_of_design

        recipients = [
            get_head_of_design(),
            design_request.requested_by,
            design_request.assigned_designer,
        ]
        title = f'Design Approved: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has been approved by compliance.'
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_hod_fast_complete(design_request):
        recipients = [
            design_request.requested_by,
            design_request.assigned_designer,
        ]
        title = f'Design Completed: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has been fast-tracked to completed.'
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_approved(design_request):
        recipients = [
            design_request.requested_by,
            design_request.assigned_designer,
            design_request.verified_by,
        ]
        title = f'Design Approved: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has been approved.'
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )

    @staticmethod
    def on_completed(design_request):
        recipients = [
            design_request.requested_by,
            design_request.assigned_designer,
        ]
        title = f'Design Completed: {design_request.design_number}'
        message = (
            f'Design {design_request.design_number} has been marked as completed.'
        )
        NotificationService._notify_many(
            recipients, NotificationType.WORKFLOW, title, message, design_request,
        )


def notify_workflow_transition(design, action, actor):
    """Dispatch workflow notifications for a completed transition action."""
    handlers = {
        'submit_request': NotificationService.on_request_created,
        'acknowledge': NotificationService.on_request_acknowledged,
        'assign': NotificationService.on_designer_assigned,
        'accept_assignment': NotificationService.on_assignment_accepted,
        'submit_work': NotificationService.on_work_submitted,
        'request_correction': NotificationService.on_correction_required,
        'resubmit': NotificationService.on_work_submitted,
        'send_to_verification': _notify_send_to_verification,
        'accept_design': _notify_send_to_verification,
        'verification_correction': NotificationService.on_verification_correction,
        'forward_to_designer': NotificationService.on_correction_required,
        'verify_approved': NotificationService.on_verification_approved,
        'send_to_compliance': NotificationService.on_sent_to_compliance,
        'compliance_correction': NotificationService.on_compliance_correction,
        'compliance_approved': NotificationService.on_compliance_approved,
        'hod_fast_complete': NotificationService.on_hod_fast_complete,
        'complete': NotificationService.on_completed,
    }
    handler = handlers.get(action)
    if handler:
        if action == 'accept_assignment':
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
