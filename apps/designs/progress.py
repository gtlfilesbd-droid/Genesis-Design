from apps.designs.models import DesignStatus

PROGRESS_STEPS = [
    ('submitted', 'Request Submitted'),
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
    DesignStatus.ENGINEER_PENDING_ACK: 'submitted',
    DesignStatus.ENGINEER_IN_PROGRESS: 'site_engineer',
    DesignStatus.NEW_REQUEST: 'hod_ack',
    DesignStatus.ACKNOWLEDGED: 'assigned',
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

STATUS_STEP_LABELS = {
    DesignStatus.NEW_REQUEST: 'Awaiting HOD Acknowledgement',
    DesignStatus.ACKNOWLEDGED: 'Pending Assignment',
}


def _step_index(step_key):
    return STEP_KEYS.index(step_key)


def _resolve_active_key(design):
    """Active step from status, capped by actual workflow completion."""
    key = STATUS_TO_STEP_KEY.get(design.status, 'submitted')

    if design.assigned_site_engineer_id and not design.engineer_submitted_at:
        if design.status == DesignStatus.ENGINEER_PENDING_ACK:
            return 'submitted'
        if design.status == DesignStatus.ENGINEER_IN_PROGRESS:
            return 'site_engineer'

    return key


def _is_step_done(design, step_key):
    """A step is only completed when its work actually finished."""
    if step_key == 'submitted':
        return design.status not in (
            DesignStatus.DRAFT,
            DesignStatus.ENGINEER_PENDING_ACK,
        )

    if step_key == 'site_engineer':
        if design.assigned_site_engineer_id:
            return bool(design.engineer_submitted_at)
        return design.status not in (
            DesignStatus.DRAFT,
            DesignStatus.ENGINEER_PENDING_ACK,
            DesignStatus.ENGINEER_IN_PROGRESS,
        )

    if step_key == 'hod_ack':
        if design.deadline_start:
            return True
        status_key = STATUS_TO_STEP_KEY.get(design.status, 'submitted')
        return _step_index(status_key) > _step_index('hod_ack')

    active_key = _resolve_active_key(design)
    return _step_index(step_key) < _step_index(active_key)


def build_progress_steps(design):
    if design.status == DesignStatus.CANCELLED:
        return [
            {'key': key, 'label': label, 'state': 'upcoming'}
            for key, label in PROGRESS_STEPS
        ], True

    active_key = _resolve_active_key(design)
    override_label = STATUS_STEP_LABELS.get(design.status)

    progress_steps = []
    for key, label in PROGRESS_STEPS:
        if key == active_key:
            state = 'active'
            display_label = override_label or label
        elif _is_step_done(design, key):
            state = 'completed'
            display_label = label
        else:
            state = 'upcoming'
            display_label = label
        progress_steps.append({'key': key, 'label': display_label, 'state': state})

    return progress_steps, False
