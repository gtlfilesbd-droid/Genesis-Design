from django.utils import timezone

from apps.designs.models import DesignStatus


def _days_between(start, end):
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 86400, 2)


def _latest_assignment_at(design):
    assignment = design.assignments.order_by('-assigned_at').first()
    return assignment.assigned_at if assignment else None


def _first_submitted_at(design):
    submission = design.submissions.order_by('submitted_at').first()
    return submission.submitted_at if submission else None


def _design_accepted_at(design):
    review = design.reviews.filter(action='accept').order_by('created_at').first()
    return review.created_at if review else None


def _verification_approved_at(design):
    verification = design.verifications.filter(action='approved').order_by('created_at').first()
    return verification.created_at if verification else None


def _compliance_approved_at(design):
    review = design.compliance_reviews.filter(action='approved').order_by('created_at').first()
    return review.created_at if review else None


def _timer_progress(start, due, now=None):
    now = now or timezone.now()
    total = (due - start).total_seconds()
    elapsed = (now - start).total_seconds()
    if total <= 0:
        percent = 100.0
    else:
        percent = min(100.0, max(0.0, (elapsed / total) * 100))
    is_overdue = now > due
    return {
        'percent_elapsed': round(percent, 1),
        'due_date': due,
        'is_overdue': is_overdue,
        'days_remaining': max(0, (due - now).days) if not is_overdue else 0,
        'days_overdue': (now - due).days if is_overdue else 0,
    }


def get_deadline_timer_data(design):
    """Deadline progress for the currently active workflow stage."""
    status = design.status
    start = due = None

    designer_stages = {
        DesignStatus.ASSIGNED,
        DesignStatus.IN_PROGRESS,
        DesignStatus.CORRECTION_REQUIRED,
        DesignStatus.RESUBMITTED,
    }
    if status in designer_stages:
        start = _latest_assignment_at(design)
        due = design.due_date
    elif status == DesignStatus.VERIFICATION_PENDING_ACK:
        start = design.verification_assigned_at
        due = design.verification_due_date
    elif status in (DesignStatus.VERIFICATION_PENDING, DesignStatus.VERIFICATION_CORRECTION):
        start = design.verification_acknowledged_at or design.verification_assigned_at
        due = design.verification_due_date
    elif status == DesignStatus.COMPLIANCE_PENDING_ACK:
        start = design.compliance_assigned_at
        due = design.compliance_due_date
    elif status in (DesignStatus.COMPLIANCE_PENDING, DesignStatus.COMPLIANCE_CORRECTION):
        start = design.compliance_acknowledged_at or design.compliance_assigned_at
        due = design.compliance_due_date
    elif status == DesignStatus.ACKNOWLEDGED:
        start = design.deadline_start
        due = design.deadline_due

    if not start or not due:
        return None

    data = _timer_progress(start, due)
    pct = data['percent_elapsed']
    if data['is_overdue'] or pct >= 80:
        data['bar_color'] = 'red'
    elif pct >= 50:
        data['bar_color'] = 'amber'
    else:
        data['bar_color'] = 'green'
    return data


def get_time_breakdown_data(design):
    """Stage-by-stage elapsed time from real workflow timestamps."""
    breakdown = []
    requested_at = design.created_at
    acknowledged_at = design.deadline_start

    if requested_at and acknowledged_at:
        breakdown.append({
            'label': 'Request to Acknowledgement',
            'days': _days_between(requested_at, acknowledged_at),
        })

    assigned_at = _latest_assignment_at(design)
    if acknowledged_at and assigned_at:
        breakdown.append({
            'label': 'Acknowledgement to Assignment',
            'days': _days_between(acknowledged_at, assigned_at),
        })

    submitted_at = _first_submitted_at(design)
    if assigned_at and submitted_at:
        breakdown.append({
            'label': 'Design Work Time',
            'days': _days_between(assigned_at, submitted_at),
        })

    accepted_at = _design_accepted_at(design)
    if submitted_at and accepted_at:
        breakdown.append({
            'label': 'Review Time (Head of Design)',
            'days': _days_between(submitted_at, accepted_at),
        })

    if design.verification_assigned_at and design.verification_acknowledged_at:
        breakdown.append({
            'label': 'Wait Time Before Verifier Acknowledged',
            'days': _days_between(
                design.verification_assigned_at,
                design.verification_acknowledged_at,
            ),
        })

    verification_approved_at = _verification_approved_at(design)
    if design.verification_acknowledged_at and verification_approved_at:
        breakdown.append({
            'label': 'Verification Time',
            'days': _days_between(
                design.verification_acknowledged_at,
                verification_approved_at,
            ),
        })

    if design.compliance_assigned_at and design.compliance_acknowledged_at:
        breakdown.append({
            'label': 'Wait Time Before Compliance Acknowledged',
            'days': _days_between(
                design.compliance_assigned_at,
                design.compliance_acknowledged_at,
            ),
        })

    compliance_approved_at = _compliance_approved_at(design)
    if design.compliance_acknowledged_at and compliance_approved_at:
        breakdown.append({
            'label': 'Compliance Review Time',
            'days': _days_between(
                design.compliance_acknowledged_at,
                compliance_approved_at,
            ),
        })

    end_point = design.completion_date or timezone.now()
    total_days = _days_between(requested_at, end_point)

    valid_stages = [row for row in breakdown if row['days'] is not None]
    slowest_stage = max(valid_stages, key=lambda row: row['days']) if valid_stages else None

    return {
        'stages': valid_stages,
        'total_days': total_days,
        'slowest_stage': slowest_stage,
    }
