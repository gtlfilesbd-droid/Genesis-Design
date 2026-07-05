"""Human-readable activity log titles and descriptions for workflow events."""

from django.utils import timezone


def _actor_name(user):
    if not user:
        return 'System'
    return user.get_full_name() or user.username


def _person_name(user):
    if not user:
        return 'someone'
    return user.get_full_name() or user.username


def _drawing_type(design):
    if design.drawing_type_id:
        return design.drawing_type.name
    return 'design'


def _format_due_date(value):
    if not value:
        return '—'
    if hasattr(value, 'hour'):
        return timezone.localtime(value).strftime('%d %b %Y')
    return value.strftime('%d %b %Y')


ACTIVITY_TITLES = {
    'submit_request': 'Design request created',
    'design_requested': 'Design request created',
    'acknowledge': 'Request acknowledged',
    'assign': 'Designer assigned',
    'accept_assignment': 'Assignment accepted',
    'submit_work': 'Work submitted',
    'start_review': 'Review started',
    'request_correction': 'Correction required',
    'resubmit': 'Work resubmitted',
    'accept_design': 'Design accepted',
    'send_to_verification': 'Sent for verification',
    'accept_verification': 'Verification acknowledged',
    'verify_approved': 'Verification approved',
    'verification_correction': 'Correction required',
    'forward_to_designer': 'Forwarded to designer',
    'send_to_compliance': 'Sent for compliance review',
    'accept_compliance': 'Compliance acknowledged',
    'compliance_approved': 'Compliance approved',
    'compliance_correction': 'Correction required',
    'complete': 'Design marked completed',
    'hod_fast_complete': 'Design marked completed',
    'cancel': 'Design request cancelled',
    'cancelled': 'Design request cancelled',
    'acknowledge_engineer': 'Site design lead acknowledged',
    'submit_engineer_review': 'Site review submitted',
    'comment_added': 'Comment added',
    'project_created': 'Project created',
    'project_updated': 'Project updated',
}


def activity_title(action):
    return ACTIVITY_TITLES.get(action, action.replace('_', ' ').title())


def build_workflow_activity_description(
    action,
    user,
    design,
    comments='',
    hod_self_assigned=False,
    **kwargs,
):
    actor = _actor_name(user)
    drawing_type = _drawing_type(design)

    if action in ('submit_request', 'design_requested'):
        return f'{actor} submitted a new {drawing_type} request'

    if action == 'acknowledge':
        return f'{actor} (Head of Design) acknowledged this request'

    if action == 'acknowledge_engineer':
        return f'{actor} acknowledged the site design work assignment'

    if action == 'submit_engineer_review':
        return f'{actor} submitted site review notes for Head of Design review'

    if action == 'assign':
        designer = kwargs.get('designer') or design.assigned_designer
        designer_name = _person_name(designer)
        due_date = _format_due_date(kwargs.get('due_date') or design.due_date)
        if hod_self_assigned:
            return f'{actor} assigned this design to themselves · Due {due_date}'
        return f'{actor} assigned {designer_name} as designer · Due {due_date}'

    if action == 'accept_assignment':
        return f'{actor} accepted the assignment and started work'

    if action == 'submit_work':
        return f'{actor} submitted completed work for review'

    if action == 'start_review':
        return f'{actor} started reviewing the submitted design'

    if action == 'request_correction':
        comment = comments or 'See feedback'
        return f'{actor} requested correction: "{comment}"'

    if action == 'resubmit':
        version = design.submissions.count() or design.revision_count + 1
        return f'{actor} resubmitted the corrected design (Version {version})'

    if action == 'accept_design':
        return f'{actor} accepted the submitted design'

    if action in ('send_to_verification',):
        verifier = kwargs.get('verifier') or design.assigned_verifier
        verifier_name = _person_name(verifier)
        due_date = _format_due_date(kwargs.get('due_date') or design.verification_due_date)
        return (
            f'{actor} forwarded this design to {verifier_name} for verification '
            f'· Due {due_date}'
        )

    if action == 'accept_verification':
        return f'{actor} acknowledged the verification request'

    if action == 'verify_approved':
        return f'{actor} approved the design after verification'

    if action == 'verification_correction':
        comment = comments or 'See feedback'
        return f'{actor} requested correction during verification: "{comment}"'

    if action == 'forward_to_designer':
        designer_name = _person_name(design.assigned_designer)
        return f'{actor} forwarded the design back to {designer_name} for correction'

    if action == 'send_to_compliance':
        officer = kwargs.get('compliance_officer') or design.assigned_compliance_officer
        officer_name = _person_name(officer)
        due_date = _format_due_date(kwargs.get('due_date') or design.compliance_due_date)
        return (
            f'{actor} forwarded this design to {officer_name} for compliance review '
            f'· Due {due_date}'
        )

    if action == 'accept_compliance':
        return f'{actor} acknowledged the compliance review request'

    if action == 'compliance_approved':
        return f'{actor} approved the design after compliance review'

    if action == 'compliance_correction':
        comment = comments or 'See feedback'
        return f'{actor} requested correction during compliance review: "{comment}"'

    if action in ('complete', 'hod_fast_complete'):
        return f'{actor} marked this design as completed'

    if action in ('cancel', 'cancelled'):
        return f'{actor} cancelled this design request'

    return f'{actor} updated this request'


def build_project_activity_description(action, user, design, **context):
    design_number = design.design_number if hasattr(design, 'design_number') else design
    description = build_workflow_activity_description(action, user, design, **context)
    return f'Design {design_number}: {description}'
