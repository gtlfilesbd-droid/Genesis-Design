from datetime import datetime, time

from django.utils import timezone

from apps.core.activity_messages import activity_title
from apps.core.models import ActivityLog
from apps.designs.models import DesignRequest, DesignStatus
from apps.workflow.action_sla import (
    ACTION_SLA_CONFIG,
    compute_action_due_at,
)

ACTION_ROLE_LABELS = {
    'submit_request': 'Requester',
    'design_requested': 'Requester',
    'acknowledge_engineer': 'Site Engineer',
    'submit_engineer_review': 'Site Engineer',
    'acknowledge': 'Head of Design',
    'assign': 'Head of Design',
    'accept_assignment': 'Designer',
    'submit_work': 'Designer',
    'resubmit': 'Designer',
    'start_review': 'Head of Design',
    'request_correction': 'Head of Design',
    'accept_design': 'Head of Design',
    'send_to_verification': 'Head of Design',
    'accept_verification': 'Verifier',
    'verify_approved': 'Verifier',
    'verification_correction': 'Head of Design',
    'forward_to_designer': 'Head of Design',
    'send_to_compliance': 'Head of Design',
    'accept_compliance': 'Compliance',
    'compliance_approved': 'Compliance',
    'compliance_correction': 'Head of Design',
    'complete': 'Head of Design',
    'hod_fast_complete': 'Head of Design',
    'cancelled': 'Requester',
    'cancel': 'Requester',
}

DELAY_SOURCE_STAGE_MATCH = {
    'Designer': ('Designer', 'submit_work', 'resubmit', 'accept_assignment', 'in_progress'),
    'Head of Design': ('Head of Design', 'acknowledge', 'assign', 'start_review', 'HOD'),
    'Site Engineer': ('Site Engineer', 'acknowledge_engineer', 'submit_engineer_review', 'engineer'),
    'Verification Team': ('Verifier', 'accept_verification', 'verify_approved', 'verification'),
    'Compliance Team': ('Compliance', 'accept_compliance', 'compliance_approved', 'compliance'),
}


def _person_name(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _days_between(start, end):
    if not start or not end:
        return None
    return round((end - start).total_seconds() / 86400, 1)


def _target_end_datetime(target_date):
    if not target_date:
        return None
    return timezone.make_aware(datetime.combine(target_date, time(23, 59, 59)))


def _latest_assignment_at(design):
    assignment = design.assignments.order_by('-assigned_at').first()
    return assignment.assigned_at if assignment else None


def _latest_submission_at(design):
    submission = design.submissions.order_by('-version_number').first()
    return submission.submitted_at if submission else None


def _anchor_for_status(design, status):
    if status == DesignStatus.ENGINEER_PENDING_ACK:
        return design.engineer_assigned_at or design.created_at
    if status == DesignStatus.ENGINEER_IN_PROGRESS:
        return design.engineer_acknowledged_at or design.engineer_assigned_at or design.created_at
    if status == DesignStatus.NEW_REQUEST:
        return design.engineer_submitted_at or design.created_at
    if status == DesignStatus.ACKNOWLEDGED:
        return design.deadline_start or design.created_at
    if status == DesignStatus.ASSIGNED:
        return design.assigned_at or _latest_assignment_at(design)
    if status in (DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW):
        return _latest_submission_at(design) or design.updated_at
    if status == DesignStatus.VERIFICATION_PENDING_ACK:
        return design.verification_assigned_at
    if status == DesignStatus.COMPLIANCE_PENDING_ACK:
        return design.compliance_assigned_at
    return design.created_at


def _empty_delay_fields():
    return {
        'is_delayed': False,
        'delayed_by': '',
        'delay_days': None,
        'delay_type': 'none',
        'delay_note': '',
    }


def _action_sla_delay(design, old_status, completed_at, actor_name):
    if not old_status or old_status not in ACTION_SLA_CONFIG:
        return None
    anchor = _anchor_for_status(design, old_status)
    due = compute_action_due_at(anchor, old_status)
    if not due or not completed_at or completed_at <= due:
        return None
    days = _days_between(due, completed_at)
    return {
        'is_delayed': True,
        'delayed_by': actor_name,
        'delay_days': days,
        'delay_type': 'action_sla',
        'delay_note': f'{days:g} days past action SLA',
    }


def _target_overdue_delay(design, row_timestamp, actor_name):
    target_end = _target_end_datetime(design.target_completion_date)
    if not target_end or not row_timestamp:
        return None
    completion = design.completion_date
    if completion and row_timestamp > completion:
        return None
    if row_timestamp <= target_end:
        return None
    if completion and completion.date() <= design.target_completion_date:
        return None
    days = _days_between(target_end, row_timestamp)
    return {
        'is_delayed': True,
        'delayed_by': actor_name,
        'delay_days': days,
        'delay_type': 'target_overdue',
        'delay_note': f'{days:g} days past request target date',
    }


def _matches_delay_source(row, delay_source):
    if not delay_source:
        return False
    needles = DELAY_SOURCE_STAGE_MATCH.get(delay_source, (delay_source,))
    haystack = f"{row.get('stage', '')} {row.get('role', '')} {row.get('action', '')}".lower()
    return any(n.lower() in haystack for n in needles)


def _make_row(stage, actor, role, timestamp, action='', notes='', duration_days=None):
    row = {
        'stage': stage,
        'actor': actor,
        'role': role,
        'timestamp': timestamp,
        'duration_days': duration_days,
        'action': action,
        'notes': notes,
        **_empty_delay_fields(),
    }
    return row


def _apply_delay_markers(design, rows):
    primary_source = (design.delay_source or '').strip()
    primary_days = design.delay_duration_days
    primary_applied = False

    for index, row in enumerate(rows):
        actor = row.get('actor') or ''
        timestamp = row.get('timestamp')

        if index + 1 < len(rows):
            next_ts = rows[index + 1]['timestamp']
            if timestamp and next_ts:
                row['duration_days'] = _days_between(timestamp, next_ts)

        sla_status = row.get('sla_status')
        if sla_status:
            sla_delay = _action_sla_delay(design, sla_status, timestamp, actor)
            if sla_delay:
                row.update(sla_delay)
                continue

        if not row['is_delayed']:
            target_delay = _target_overdue_delay(design, timestamp, actor)
            if target_delay:
                row.update(target_delay)

        if primary_source and not primary_applied and _matches_delay_source(row, primary_source):
            row['is_delayed'] = True
            row['delay_type'] = 'primary_delay'
            row['delayed_by'] = actor or primary_source
            row['delay_days'] = float(primary_days) if primary_days is not None else row.get('delay_days')
            row['delay_note'] = f'Primary delay source ({primary_source})'
            primary_applied = True

    return rows


def _build_rows_from_logs(design):
    rows = []
    logs = ActivityLog.objects.filter(
        entity_type='design_request',
        entity_id=design.pk,
    ).select_related('user').order_by('created_at')

    has_submit = False
    for log in logs:
        action = log.action
        if action in ('comment_added',):
            continue
        if action in ('submit_request', 'design_requested'):
            has_submit = True
        metadata = log.metadata or {}
        old_status = metadata.get('old_status')
        stage = activity_title(action)
        actor = _person_name(log.user)
        role = ACTION_ROLE_LABELS.get(action, '')
        notes = log.description or ''
        if metadata.get('comments'):
            notes = metadata['comments'] if not notes else notes

        row = _make_row(stage, actor, role, log.created_at, action=action, notes=notes)
        row['sla_status'] = old_status
        rows.append(row)

    if not has_submit:
        rows.insert(0, _make_row(
            'Request Submitted',
            _person_name(design.requested_by),
            'Requester',
            design.created_at,
            action='design_requested',
            notes=f'Target date: {design.target_completion_date}' if design.target_completion_date else '',
        ))

    if design.assigned_site_engineer_id and design.engineer_assigned_at:
        has_engineer_assign = any(r.get('action') == 'acknowledge_engineer' for r in rows)
        if not has_engineer_assign and design.engineer_assigned_at:
            insert_at = 1 if rows else 0
            rows.insert(insert_at, _make_row(
                'Site Engineer Assigned',
                _person_name(design.assigned_site_engineer),
                'Site Engineer',
                design.engineer_assigned_at,
                notes=f'Due: {timezone.localtime(design.engineer_due_date).strftime("%d %b %Y")}' if design.engineer_due_date else '',
            ))

    rows.sort(key=lambda r: r['timestamp'] or design.created_at)
    return rows


def build_workflow_audit_report(design):
    rows = _build_rows_from_logs(design)
    rows = _apply_delay_markers(design, rows)

    completed_late = bool(
        design.completion_date
        and design.target_completion_date
        and design.completion_date.date() > design.target_completion_date
    )
    delay_summary = None
    if design.delay_source:
        delay_summary = {
            'primary_source': design.delay_source,
            'primary_days': float(design.delay_duration_days) if design.delay_duration_days is not None else None,
            'completed_late': completed_late,
        }

    return {
        'design_number': design.design_number,
        'project': design.project.name,
        'project_code': design.project.code,
        'requested_by': _person_name(design.requested_by),
        'target_completion_date': design.target_completion_date,
        'status': design.get_status_display(),
        'delay_summary': delay_summary,
        'rows': rows,
    }


def get_audit_report_for_design_number(design_number):
    if not design_number:
        return None
    design = DesignRequest.objects.select_related(
        'project', 'requested_by', 'assigned_site_engineer',
        'assigned_designer', 'assigned_verifier', 'assigned_compliance_officer',
    ).filter(design_number__iexact=design_number.strip()).first()
    if not design:
        return None
    return build_workflow_audit_report(design)
