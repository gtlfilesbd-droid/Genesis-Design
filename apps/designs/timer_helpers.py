from datetime import datetime, time

from django.utils import timezone

from apps.designs.models import DesignStatus
from apps.workflow.action_sla import ACTION_SLA_STATUSES, get_action_due_at, get_action_anchor

_DELAY_SOURCE_TO_STAGE = {
    'Designer': 'Designer',
    'Verification Team': 'Verifier',
    'Compliance Team': 'Compliance',
}


def _days_between(start, end):
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 86400, 2)


def _timeline_days_between(start, end):
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 86400, 1)


def _target_end_datetime(target_date):
    if not target_date:
        return None
    return timezone.make_aware(datetime.combine(target_date, time(23, 59, 59)))


def _target_start_datetime(target_date):
    if not target_date:
        return None
    return timezone.make_aware(datetime.combine(target_date, time(0, 0, 0)))


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
    elif status in ACTION_SLA_STATUSES:
        start = get_action_anchor(design)
        due = get_action_due_at(design)
    elif status == DesignStatus.ENGINEER_IN_PROGRESS:
        start = design.engineer_acknowledged_at or design.engineer_assigned_at
        due = design.engineer_due_date
    elif status in (DesignStatus.VERIFICATION_PENDING, DesignStatus.VERIFICATION_CORRECTION):
        start = design.verification_acknowledged_at or design.verification_assigned_at
        due = design.verification_due_date
    elif status in (DesignStatus.COMPLIANCE_PENDING, DesignStatus.COMPLIANCE_CORRECTION):
        start = design.compliance_acknowledged_at or design.compliance_assigned_at
        due = design.compliance_due_date

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


def _segment_class(stage):
    if stage['is_current_delay_source']:
        return 'segment-delay'
    if stage['name'] == 'Compliance':
        return 'segment-delay' if stage['is_ongoing'] else 'segment-verifier'
    if stage['name'] == 'Verifier':
        return 'segment-verifier'
    if stage['is_ongoing']:
        return 'segment-ongoing'
    return 'segment-designer'


def _legend_class(stage):
    if stage['is_current_delay_source']:
        return 'legend-delay'
    if stage['name'] == 'Compliance':
        return 'legend-delay' if stage['is_ongoing'] else 'legend-verifier'
    if stage['name'] == 'Verifier':
        return 'legend-verifier'
    if stage['is_ongoing']:
        return 'legend-ongoing'
    return 'legend-designer'


def _resolve_completed_late_delay_stage(design, stages):
    mapped = _DELAY_SOURCE_TO_STAGE.get(design.delay_source)
    if mapped:
        for stage in stages:
            if stage['name'] == mapped:
                return stage
    valid = [s for s in stages if s['days'] is not None]
    return max(valid, key=lambda row: row['days']) if valid else None


def get_completion_timeline_data(design):
    """Build stage-by-stage timeline data for the visual completion bar."""
    stages = []
    now_time = timezone.now()
    target = design.target_completion_date
    target_end = _target_end_datetime(target)
    requested_at = design.created_at

    assigned_at = _latest_assignment_at(design)
    submitted_at = _first_submitted_at(design)

    if assigned_at:
        design_end = submitted_at or now_time
        stages.append({
            'name': 'Designer',
            'person': design.assigned_designer.get_full_name() if design.assigned_designer else None,
            'start': assigned_at,
            'end': submitted_at,
            'days': _timeline_days_between(assigned_at, design_end),
            'is_ongoing': submitted_at is None,
            'is_current_delay_source': False,
        })

    verification_approved_at = _verification_approved_at(design)
    if design.verification_acknowledged_at:
        verify_end = verification_approved_at or now_time
        stages.append({
            'name': 'Verifier',
            'person': design.assigned_verifier.get_full_name() if design.assigned_verifier else None,
            'start': design.verification_acknowledged_at,
            'end': verification_approved_at,
            'days': _timeline_days_between(design.verification_acknowledged_at, verify_end),
            'is_ongoing': verification_approved_at is None,
            'is_current_delay_source': False,
        })

    compliance_approved_at = _compliance_approved_at(design)
    if design.compliance_acknowledged_at:
        compliance_end = compliance_approved_at or now_time
        stages.append({
            'name': 'Compliance',
            'person': (
                design.assigned_compliance_officer.get_full_name()
                if design.assigned_compliance_officer else None
            ),
            'start': design.compliance_acknowledged_at,
            'end': compliance_approved_at,
            'days': _timeline_days_between(design.compliance_acknowledged_at, compliance_end),
            'is_ongoing': compliance_approved_at is None,
            'is_current_delay_source': False,
        })

    if not stages:
        return None

    overall_end = design.completion_date or now_time
    total_days = _timeline_days_between(requested_at, overall_end)

    is_completed_on_time = bool(
        design.completion_date and target
        and design.completion_date.date() <= target
    )
    is_completed_late = bool(
        design.completion_date and target
        and design.completion_date.date() > target
    )
    is_overdue = bool(
        target and not design.completion_date
        and overall_end.date() > target
    )

    days_over = None
    if is_overdue and target_end:
        days_over = _timeline_days_between(target_end, overall_end)
    elif is_completed_late and target_end:
        days_over = _timeline_days_between(target_end, design.completion_date)

    if is_overdue:
        for stage in stages:
            if stage['is_ongoing']:
                stage['is_current_delay_source'] = True
                break
    elif is_completed_late:
        delay_stage = _resolve_completed_late_delay_stage(design, stages)
        if delay_stage:
            delay_stage['is_current_delay_source'] = True

    days_allowed = _timeline_days_between(requested_at, target_end) if target_end else None

    days_remaining = None
    if target_end and not is_overdue and not design.completion_date:
        remaining = _timeline_days_between(now_time, target_end)
        if remaining is not None and remaining >= 0:
            days_remaining = remaining

    target_marker_position_percent = None
    if target and requested_at:
        total_span = (overall_end - requested_at).total_seconds()
        if total_span > 0:
            marker_point = _target_start_datetime(target)
            elapsed_to_target = (marker_point - requested_at).total_seconds()
            target_marker_position_percent = round(
                min(100, max(0, (elapsed_to_target / total_span) * 100)), 1
            )

    delay_info = None
    delay_stage = next((s for s in stages if s['is_current_delay_source']), None)
    if delay_stage and (is_overdue or is_completed_late):
        delay_info = {
            'stage_name': delay_stage['name'],
            'person': delay_stage['person'],
            'start': delay_stage['start'],
        }

    for stage in stages:
        stage['segment_class'] = _segment_class(stage)
        stage['legend_class'] = _legend_class(stage)

    return {
        'stages': stages,
        'total_days': total_days,
        'days_allowed': days_allowed,
        'target_date': target,
        'is_overdue': is_overdue,
        'is_completed_on_time': is_completed_on_time,
        'is_completed_late': is_completed_late,
        'days_over': days_over,
        'days_remaining': days_remaining,
        'target_marker_position_percent': target_marker_position_percent,
        'delay_info': delay_info,
    }
