"""Human-readable notification message templates for workflow events."""


def _person_name(user):
    if not user:
        return 'Someone'
    return user.get_full_name() or user.username


def _drawing_type(design_request):
    if design_request.drawing_type_id:
        return design_request.drawing_type.name
    return 'design'


def _project_label(design_request):
    if not design_request.project_id:
        return 'the project'
    project = design_request.project
    return f'{project.name} ({project.code})'


def _format_due_date(design_request):
    due = (
        design_request.engineer_due_date
        or design_request.due_date
        or design_request.verification_due_date
        or design_request.compliance_due_date
    )
    if due:
        return due.strftime('%d %b %Y')
    return '—'


def request_created_message(design_request):
    requester = _person_name(design_request.requested_by)
    return (
        f'{requester} submitted a new {_drawing_type(design_request)} request '
        f'for {_project_label(design_request)}'
    )


def acknowledged_message(design_request, hod_name):
    return (
        f'Your request for {_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has been acknowledged by {hod_name}'
    )


def designer_assigned_message(design_request):
    return (
        f"You've been assigned to design {_drawing_type(design_request)} "
        f'for {_project_label(design_request)} · Due {_format_due_date(design_request)}'
    )


def designer_assigned_requester_message(design_request):
    designer = _person_name(design_request.assigned_designer)
    return (
        f'{designer} has been assigned to your {_drawing_type(design_request)} request '
        f'for {_project_label(design_request)}'
    )


def engineer_assigned_message(design_request):
    due = design_request.engineer_due_date
    due_label = due.strftime('%d %b %Y') if due else '—'
    return (
        f"You've been assigned as site design lead for {_drawing_type(design_request)} "
        f'for {_project_label(design_request)} · Due {due_label}'
    )


def engineer_assigned_requester_message(design_request):
    engineer = _person_name(design_request.assigned_site_engineer)
    return (
        f'{engineer} has been assigned as site design lead for your '
        f'{_drawing_type(design_request)} request for {_project_label(design_request)}'
    )


def engineer_acknowledged_message(design_request, engineer_name):
    return (
        f'{engineer_name} acknowledged the site design work request for '
        f'{_drawing_type(design_request)} ({_project_label(design_request)})'
    )


def engineer_submitted_message(design_request):
    engineer = _person_name(design_request.assigned_site_engineer)
    return (
        f'{engineer} submitted site review for {_drawing_type(design_request)} '
        f'({_project_label(design_request)}) — ready for Head of Design'
    )


def work_submitted_message(design_request):
    designer = _person_name(design_request.assigned_designer)
    return (
        f'{designer} submitted {_drawing_type(design_request)} '
        f'({_project_label(design_request)}) for your review'
    )


def correction_required_message(design_request, comment=''):
    text = comment or 'See feedback on the request'
    return (
        f'Correction needed on {_drawing_type(design_request)} '
        f'({_project_label(design_request)}): "{text}"'
    )


def design_accepted_message(design_request):
    return (
        f'Your design for {_drawing_type(design_request)} '
        f'({_project_label(design_request)}) has been accepted'
    )


def sent_to_verification_message(design_request):
    return (
        f"You've been asked to verify {_drawing_type(design_request)} "
        f'for {_project_label(design_request)} · Due {_format_due_date(design_request)}'
    )


def verification_acknowledged_message(design_request, verifier_name):
    return (
        f'{verifier_name} has started verifying {_drawing_type(design_request)} '
        f'({_project_label(design_request)})'
    )


def verification_approved_message(design_request, verifier_name):
    return (
        f'{verifier_name} approved {_drawing_type(design_request)} '
        f'({_project_label(design_request)}) after verification'
    )


def verification_correction_message(design_request, comment=''):
    text = comment or 'See feedback on the request'
    return (
        f'Verification correction needed on {_drawing_type(design_request)} '
        f'({_project_label(design_request)}): "{text}"'
    )


def sent_to_compliance_message(design_request):
    return (
        f"You've been asked to review {_drawing_type(design_request)} "
        f'for {_project_label(design_request)} for compliance '
        f'· Due {_format_due_date(design_request)}'
    )


def compliance_acknowledged_message(design_request, compliance_name):
    return (
        f'{compliance_name} has started compliance review on {_drawing_type(design_request)} '
        f'({_project_label(design_request)})'
    )


def compliance_approved_message(design_request, compliance_name):
    return (
        f'{compliance_name} approved {_drawing_type(design_request)} '
        f'({_project_label(design_request)}) after compliance review'
    )


def compliance_correction_message(design_request, comment=''):
    text = comment or 'See feedback on the request'
    return (
        f'Compliance correction needed on {_drawing_type(design_request)} '
        f'({_project_label(design_request)}): "{text}"'
    )


def design_approved_message(design_request):
    return (
        f'{_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has received final approval'
    )


def design_completed_message(design_request):
    return (
        f'{_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has been marked completed'
    )


def assignment_accepted_message(design_request, actor):
    actor_name = _person_name(actor)
    return (
        f'{actor_name} accepted the assignment for {_drawing_type(design_request)} '
        f'({_project_label(design_request)})'
    )


def sent_to_compliance_requester_message(design_request):
    return (
        f'{_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has been sent for compliance review'
    )


def hod_fast_complete_message(design_request):
    return (
        f'{_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has been fast-tracked to completed'
    )


def compliance_approved_hod_message(design_request):
    return (
        f'{_drawing_type(design_request)} ({_project_label(design_request)}) '
        f'has been approved by compliance'
    )
