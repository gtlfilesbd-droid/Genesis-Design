from apps.designs.models import DesignStatus

PROGRESS_STEPS = [
    ('submitted', 'Request Submitted'),
    ('request_under_review', 'Under Review'),
    ('site_engineer', 'Site Verification'),
    ('hod_ack', 'HOD Acknowledgement'),
    ('assigned', 'Designer Assigned'),
    ('in_progress', 'Design In Progress'),
    ('under_review', 'HOD Review'),
    ('verification_pending', 'Verification'),
    ('compliance_pending', 'Compliance'),
    ('approved', 'Approved'),
    ('completed', 'Completed'),
]

STEP_KEYS = [step[0] for step in PROGRESS_STEPS]

STATUS_TO_STEP_KEY = {
    DesignStatus.DRAFT: 'submitted',
    DesignStatus.REQUEST_UNDER_REVIEW: 'request_under_review',
    DesignStatus.ENGINEER_PENDING_ACK: 'site_engineer',
    DesignStatus.ENGINEER_IN_PROGRESS: 'site_engineer',
    DesignStatus.NEW_REQUEST: 'site_engineer',
    DesignStatus.ACKNOWLEDGED: 'hod_ack',
    DesignStatus.ASSIGNED: 'assigned',
    DesignStatus.IN_PROGRESS: 'in_progress',
    DesignStatus.SUBMITTED: 'under_review',
    DesignStatus.UNDER_REVIEW: 'under_review',
    DesignStatus.CORRECTION_REQUIRED: 'under_review',
    DesignStatus.RESUBMITTED: 'in_progress',
    DesignStatus.VERIFICATION_PENDING_ACK: 'verification_pending',
    DesignStatus.VERIFICATION_PENDING: 'verification_pending',
    DesignStatus.VERIFICATION_CORRECTION: 'verification_pending',
    DesignStatus.AWAITING_COMPLIANCE: 'compliance_pending',
    DesignStatus.COMPLIANCE_PENDING_ACK: 'compliance_pending',
    DesignStatus.COMPLIANCE_PENDING: 'compliance_pending',
    DesignStatus.COMPLIANCE_CORRECTION: 'compliance_pending',
    DesignStatus.FINAL_APPROVAL_PENDING: 'compliance_pending',
    DesignStatus.APPROVED: 'approved',
    DesignStatus.COMPLETED: 'completed',
}


def _resolve_current_index(design):
    step_key = STATUS_TO_STEP_KEY.get(design.status, 'submitted')
    try:
        current_index = STEP_KEYS.index(step_key)
    except ValueError:
        current_index = 0

    if design.assigned_site_engineer_id or design.main_design_lead_id:
        if design.status == DesignStatus.ENGINEER_PENDING_ACK:
            current_index = max(current_index, STEP_KEYS.index('site_engineer'))
        elif design.status == DesignStatus.ENGINEER_IN_PROGRESS:
            current_index = max(current_index, STEP_KEYS.index('site_engineer'))

    if design.status == DesignStatus.REQUEST_UNDER_REVIEW:
        current_index = STEP_KEYS.index('request_under_review')

    if design.status == DesignStatus.NEW_REQUEST:
        if design.assigned_site_engineer_id or design.main_design_lead_id:
            current_index = STEP_KEYS.index('site_engineer')
        else:
            current_index = STEP_KEYS.index('submitted')

    return current_index


def build_progress_steps(design):
    if design.status == DesignStatus.CANCELLED:
        return [
            {'key': key, 'label': label, 'state': 'upcoming'}
            for key, label in PROGRESS_STEPS
        ], True

    current_index = _resolve_current_index(design)

    progress_steps = []
    for index, (key, label) in enumerate(PROGRESS_STEPS):
        if index < current_index:
            state = 'completed'
        elif index == current_index:
            state = 'active'
        else:
            state = 'upcoming'
        progress_steps.append({'key': key, 'label': label, 'state': state})

    return progress_steps, False
