from datetime import date, datetime, time

from django.utils import timezone

from apps.core.activity_messages import activity_title
from apps.core.models import ActivityLog
from apps.designs.models import DesignRequest, DesignStatus
from apps.workflow.action_sla import (
    ACTION_DUE_LABELS,
    ACTION_SLA_CONFIG,
    compute_action_due_at,
)

from apps.core.workflow_labels import SITE_DESIGN_LEAD_LABEL

ACTION_ROLE_LABELS = {
    'submit_request': 'Requester',
    'design_requested': 'Requester',
    'acknowledge_engineer': SITE_DESIGN_LEAD_LABEL,
    'submit_engineer_review': SITE_DESIGN_LEAD_LABEL,
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

_SITE_DESIGN_LEAD_DELAY_MATCH = (
    SITE_DESIGN_LEAD_LABEL,
    'acknowledge_engineer',
    'submit_engineer_review',
    'engineer',
)

DELAY_SOURCE_STAGE_MATCH = {
    'Designer': ('Designer', 'submit_work', 'resubmit', 'accept_assignment', 'in_progress'),
    'Head of Design': ('Head of Design', 'acknowledge', 'assign', 'start_review', 'HOD'),
    SITE_DESIGN_LEAD_LABEL: _SITE_DESIGN_LEAD_DELAY_MATCH,
    'Site Engineer': _SITE_DESIGN_LEAD_DELAY_MATCH,  # legacy delay_source values
    'Verification Team': ('Verifier', 'accept_verification', 'verify_approved', 'verification'),
    'Compliance Team': ('Compliance', 'accept_compliance', 'compliance_approved', 'compliance'),
}

DESIGNER_ACTIONS = frozenset({'accept_assignment', 'submit_work', 'resubmit'})
VERIFICATION_ACTIONS = frozenset({'accept_verification', 'verify_approved'})
COMPLIANCE_ACTIONS = frozenset({'accept_compliance', 'compliance_approved'})


def _person_name(user):
    if not user:
        return ''
    return user.get_full_name() or user.username


def _days_between(start, end):
    if not start or not end:
        return None
    start_cmp = _as_datetime(start)
    end_cmp = _as_datetime(end)
    if not start_cmp or not end_cmp:
        return None
    return round((end_cmp - start_cmp).total_seconds() / 86400, 1)


def _as_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value
    if isinstance(value, date):
        return timezone.make_aware(datetime.combine(value, time(23, 59, 59)))
    return None


def _target_end_datetime(target_date):
    if not target_date:
        return None
    return timezone.make_aware(datetime.combine(target_date, time(23, 59, 59)))


def _format_due_at(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        return timezone.localtime(value).strftime('%d %b %Y, %H:%M')
    if isinstance(value, date):
        return value.strftime('%d %b %Y')
    return str(value)


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


def _sla_due_for_status(design, status):
    if not status or status not in ACTION_SLA_CONFIG:
        return None
    anchor = _anchor_for_status(design, status)
    return compute_action_due_at(anchor, status)


def _sla_label_for_status(status):
    if not status:
        return 'Action SLA'
    return ACTION_DUE_LABELS.get(status, 'Action SLA')


def _empty_due_fields():
    return {
        'due_label': '',
        'due_at': None,
        'sla_due_at': None,
        'sla_label': '',
        'on_time_status': 'n/a',
        'status_note': '',
        'due_at_display': '',
        'sla_due_at_display': '',
    }


def _empty_delay_fields():
    return {
        'is_delayed': False,
        'delayed_by': '',
        'delay_days': None,
        'delay_type': 'none',
        'delay_note': '',
    }


def _make_row(stage, actor, role, timestamp, action='', notes='', duration_days=None):
    return {
        'stage': stage,
        'actor': actor,
        'role': role,
        'timestamp': timestamp,
        'duration_days': duration_days,
        'action': action,
        'notes': notes,
        **_empty_due_fields(),
        **_empty_delay_fields(),
    }


def _assignment_at_index(assignments, index):
    if 0 <= index < len(assignments):
        return assignments[index]
    return None


def _assignment_for_timestamp(assignments, timestamp):
    if not timestamp:
        return assignments[-1] if assignments else None
    active = None
    for assignment in assignments:
        if assignment.assigned_at <= timestamp:
            active = assignment
        else:
            break
    return active


def _compare_completion(timestamp, due_at, sla_due_at):
    if not timestamp:
        return 'n/a', ''
    ts = _as_datetime(timestamp)
    explicit_late = False
    sla_late = False
    if due_at and ts > _as_datetime(due_at):
        explicit_late = True
    if sla_due_at and ts > _as_datetime(sla_due_at):
        sla_late = True
    if explicit_late:
        days = _days_between(due_at, timestamp)
        label = f'Late by {days:g} days vs due date' if days is not None else 'Late vs due date'
        return 'late', label
    if sla_late:
        days = _days_between(sla_due_at, timestamp)
        label = f'Late by {days:g} days vs action SLA' if days is not None else 'Late vs action SLA'
        return 'late', label
    if due_at or sla_due_at:
        return 'on_time', 'Completed on time'
    return 'n/a', ''


def _resolve_row_due_dates(design, row, context):
    action = row.get('action', '')
    old_status = row.get('sla_status')
    timestamp = row.get('timestamp')
    assignments = context['assignments']
    assign_idx = context['assign_idx']
    ver_idx = context['ver_idx']
    comp_idx = context['comp_idx']

    due_label = ''
    due_at = None
    sla_due_at = None
    sla_label = ''
    on_time_status = 'n/a'
    status_note = ''

    if action in ('design_requested', 'submit_request'):
        due_label = 'Requester Target'
        due_at = design.target_completion_date
        on_time_status = 'n/a'
        status_note = 'Target date set by requester'

    elif action == 'site_engineer_assigned':
        due_label = 'Engineer Due'
        due_at = design.engineer_due_date
        on_time_status = 'due_set'
        status_note = f'Engineer due {_format_due_at(due_at)}' if due_at else 'Engineer due date set'

    elif action == 'acknowledge_engineer':
        due_label = 'Engineer Due'
        due_at = design.engineer_due_date
        sla_due_at = _sla_due_for_status(design, DesignStatus.ENGINEER_PENDING_ACK)
        sla_label = _sla_label_for_status(DesignStatus.ENGINEER_PENDING_ACK)
        on_time_status, status_note = _compare_completion(timestamp, due_at, sla_due_at)

    elif action == 'submit_engineer_review':
        due_label = 'Requester Target'
        due_at = design.target_completion_date
        on_time_status, status_note = _compare_completion(timestamp, _target_end_datetime(due_at), None)
        if on_time_status == 'n/a' and design.target_completion_date:
            status_note = 'Site review submitted'

    elif action == 'acknowledge':
        sla_due_at = _sla_due_for_status(design, DesignStatus.NEW_REQUEST)
        sla_label = _sla_label_for_status(DesignStatus.NEW_REQUEST)
        on_time_status, status_note = _compare_completion(timestamp, None, sla_due_at)

    elif action == 'assign':
        assignment = _assignment_at_index(assignments, assign_idx)
        if assignment:
            due_label = 'Designer Due (HOD)'
            due_at = assignment.due_date
            context['assign_idx'] += 1
        sla_due_at = _sla_due_for_status(design, DesignStatus.ACKNOWLEDGED)
        sla_label = _sla_label_for_status(DesignStatus.ACKNOWLEDGED)
        on_time_status = 'due_set'
        status_note = f'Designer due set to {_format_due_at(due_at)}' if due_at else 'Designer due date set'
        _, sla_note = _compare_completion(timestamp, None, sla_due_at)
        if sla_note and 'Late' in sla_note:
            on_time_status = 'late'
            status_note = sla_note

    elif action in DESIGNER_ACTIONS:
        assignment = _assignment_for_timestamp(assignments, timestamp)
        if assignment:
            due_label = 'Designer Due (HOD)'
            due_at = assignment.due_date
        sla_due_at = _sla_due_for_status(design, old_status) if old_status else None
        if old_status:
            sla_label = _sla_label_for_status(old_status)
        on_time_status, status_note = _compare_completion(timestamp, due_at, sla_due_at)

    elif action in ('send_to_verification', 'accept_design'):
        due_label = 'Verification Due'
        due_at = design.verification_due_date
        sla_due_at = _sla_due_for_status(design, old_status) if old_status else None
        if old_status:
            sla_label = _sla_label_for_status(old_status)
        on_time_status = 'due_set'
        status_note = f'Verification due set to {_format_due_at(due_at)}' if due_at else 'Verification due date set'
        context['ver_idx'] += 1

    elif action in VERIFICATION_ACTIONS:
        due_label = 'Verification Due'
        due_at = design.verification_due_date
        sla_due_at = _sla_due_for_status(design, DesignStatus.VERIFICATION_PENDING_ACK)
        sla_label = _sla_label_for_status(DesignStatus.VERIFICATION_PENDING_ACK)
        on_time_status, status_note = _compare_completion(timestamp, due_at, sla_due_at)

    elif action == 'send_to_compliance':
        due_label = 'Compliance Due'
        due_at = design.compliance_due_date
        sla_due_at = _sla_due_for_status(design, old_status) if old_status else None
        if old_status:
            sla_label = _sla_label_for_status(old_status)
        on_time_status = 'due_set'
        status_note = f'Compliance due set to {_format_due_at(due_at)}' if due_at else 'Compliance due date set'
        context['comp_idx'] += 1

    elif action in COMPLIANCE_ACTIONS:
        due_label = 'Compliance Due'
        due_at = design.compliance_due_date
        sla_due_at = _sla_due_for_status(design, DesignStatus.COMPLIANCE_PENDING_ACK)
        sla_label = _sla_label_for_status(DesignStatus.COMPLIANCE_PENDING_ACK)
        on_time_status, status_note = _compare_completion(timestamp, due_at, sla_due_at)

    elif old_status:
        sla_due_at = _sla_due_for_status(design, old_status)
        sla_label = _sla_label_for_status(old_status)
        on_time_status, status_note = _compare_completion(timestamp, None, sla_due_at)

    row['due_label'] = due_label
    row['due_at'] = due_at
    row['sla_due_at'] = sla_due_at
    row['sla_label'] = sla_label
    row['on_time_status'] = on_time_status
    row['status_note'] = status_note
    row['due_at_display'] = _format_due_at(due_at)
    row['sla_due_at_display'] = _format_due_at(sla_due_at)


def _due_breach_delay(row, actor_name):
    timestamp = row.get('timestamp')
    due_at = row.get('due_at')
    if not due_at or not timestamp:
        return None
    if _as_datetime(timestamp) <= _as_datetime(due_at):
        return None
    if row.get('on_time_status') == 'due_set':
        return None
    days = _days_between(due_at, timestamp)
    label = row.get('due_label') or 'due date'
    return {
        'is_delayed': True,
        'delayed_by': actor_name,
        'delay_days': days,
        'delay_type': 'due_breach',
        'delay_note': f'Late by {days:g} days vs {label}' if days is not None else f'Late vs {label}',
    }


def _sla_breach_delay(row, actor_name):
    timestamp = row.get('timestamp')
    sla_due_at = row.get('sla_due_at')
    if not sla_due_at or not timestamp:
        return None
    if _as_datetime(timestamp) <= _as_datetime(sla_due_at):
        return None
    if row.get('on_time_status') == 'due_set':
        return None
    days = _days_between(sla_due_at, timestamp)
    return {
        'is_delayed': True,
        'delayed_by': actor_name,
        'delay_days': days,
        'delay_type': 'action_sla',
        'delay_note': f'Late by {days:g} days vs action SLA' if days is not None else 'Late vs action SLA',
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


def _apply_due_dates(design, rows):
    assignments = list(design.assignments.order_by('assigned_at'))
    context = {
        'assignments': assignments,
        'assign_idx': 0,
        'ver_idx': 0,
        'comp_idx': 0,
    }
    for row in rows:
        _resolve_row_due_dates(design, row, context)
    return rows


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

        due_delay = _due_breach_delay(row, actor)
        if due_delay:
            row.update(due_delay)
            if row.get('on_time_status') != 'due_set':
                row['on_time_status'] = 'late'
            continue

        sla_delay = _sla_breach_delay(row, actor)
        if sla_delay:
            row.update(sla_delay)
            if row.get('on_time_status') != 'due_set':
                row['on_time_status'] = 'late'
            continue

        if not row['is_delayed']:
            target_delay = _target_overdue_delay(design, timestamp, actor)
            if target_delay:
                row.update(target_delay)
                row['on_time_status'] = 'late'

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
            notes='',
        ))

    if design.assigned_site_engineer_id and design.engineer_assigned_at:
        has_engineer_row = any(
            r.get('action') in ('acknowledge_engineer', 'site_engineer_assigned')
            for r in rows
        )
        if not has_engineer_row:
            insert_at = 1 if rows else 0
            rows.insert(insert_at, _make_row(
                f'{SITE_DESIGN_LEAD_LABEL} Assigned',
                _person_name(design.assigned_site_engineer),
                SITE_DESIGN_LEAD_LABEL,
                design.engineer_assigned_at,
                action='site_engineer_assigned',
                notes='',
            ))

    rows.sort(key=lambda r: r['timestamp'] or design.created_at)
    return rows


def _build_key_dates(design):
    return {
        'requester_target': design.target_completion_date,
        'engineer_due': design.engineer_due_date,
        'designer_due': design.due_date,
        'verification_due': design.verification_due_date,
        'compliance_due': design.compliance_due_date,
    }


def build_workflow_audit_report(design):
    rows = _build_rows_from_logs(design)
    rows = _apply_due_dates(design, rows)
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
        'key_dates': _build_key_dates(design),
        'delay_summary': delay_summary,
        'rows': rows,
    }


def format_audit_due_value(value):
    return _format_due_at(value)


def get_audit_report_for_design_number(design_number):
    if not design_number:
        return None
    design = DesignRequest.objects.select_related(
        'project', 'requested_by', 'assigned_site_engineer',
        'assigned_designer', 'assigned_verifier', 'assigned_compliance_officer',
    ).prefetch_related('assignments').filter(
        design_number__iexact=design_number.strip(),
    ).first()
    if not design:
        return None
    return build_workflow_audit_report(design)
