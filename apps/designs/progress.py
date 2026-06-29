from apps.designs.models import DesignStatus

PROGRESS_STEPS = [
    ('site_engineer', 'Site Engineer'),
    ('new', 'New Request'),
    ('acknowledged', 'Acknowledged'),
    ('assigned', 'Assigned'),
    ('in_progress', 'In Progress'),
    ('under_review', 'Under Review'),
    ('verification_pending', 'Verification Pending'),
    ('compliance_pending', 'Compliance Pending'),
    ('approved', 'Approved'),
    ('completed', 'Completed'),
]

STATUS_TO_STEP_KEY = {
    DesignStatus.DRAFT: 'site_engineer',
    DesignStatus.ENGINEER_PENDING_ACK: 'site_engineer',
    DesignStatus.ENGINEER_IN_PROGRESS: 'site_engineer',
    DesignStatus.NEW_REQUEST: 'new',
    DesignStatus.ACKNOWLEDGED: 'acknowledged',
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


def build_progress_steps(design):
    step_keys = [step[0] for step in PROGRESS_STEPS]

    if design.status == DesignStatus.CANCELLED:
        return [
            {'key': key, 'label': label, 'state': 'upcoming'}
            for key, label in PROGRESS_STEPS
        ], True

    step_key = STATUS_TO_STEP_KEY.get(design.status, 'new')
    try:
        current_index = step_keys.index(step_key)
    except ValueError:
        current_index = 0

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
