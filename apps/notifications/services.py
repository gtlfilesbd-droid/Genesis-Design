from django.core.mail import send_mail
from django.conf import settings

from .models import Notification, NotificationSetting, NotificationType


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


def notify_workflow_transition(design, action, actor):
    link = f'/requests/{design.pk}/'
    recipients = set()

    if design.current_holder:
        recipients.add(design.current_holder)
    if design.assigned_designer:
        recipients.add(design.assigned_designer)
    if design.requested_by:
        recipients.add(design.requested_by)

    recipients.discard(actor)

    title = f'Design {design.design_number} updated'
    message = (
        f'{actor.get_full_name() or actor.username} performed "{action}" on '
        f'{design.design_number}. Current status: {design.get_status_display()}.'
    )
    for user in recipients:
        create_notification(user, title, message, link)


def send_escalation(design, level):
    from apps.accounts.models import User, UserRole

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
