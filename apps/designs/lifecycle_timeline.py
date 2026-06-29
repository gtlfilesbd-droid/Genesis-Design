from datetime import datetime, time

from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.models import ActivityLog
from apps.designs.models import DesignStatus
from apps.workflow.services import get_head_of_design

HOD_ACTIONS = (
    'acknowledge', 'assign', 'request_correction', 'accept_design',
    'send_to_verification', 'forward_to_designer', 'send_to_compliance',
    'compliance_approved', 'complete', 'hod_fast_complete', 'start_review',
)

ROLE_LABELS = {
    'hod': 'Head of Design',
    'engineer': 'Site Engineer',
    'designer': 'Designer',
    'verifier': 'Verifier',
    'compliance': 'Compliance',
}

HAPPY_PATH_PENDING = [
    ('engineer', 'Site Engineer'),
    ('hod', 'Assign'),
    ('designer', 'Designer'),
    ('hod', 'HOD Review'),
    ('verifier', 'Verifier'),
    ('hod', 'HOD'),
    ('compliance', 'Compliance'),
    ('hod', 'Final Approval'),
    ('complete', 'Complete'),
]

STATUS_PENDING_START = {
    DesignStatus.ENGINEER_PENDING_ACK: 0,
    DesignStatus.ENGINEER_IN_PROGRESS: 0,
    DesignStatus.NEW_REQUEST: 1,
    DesignStatus.ACKNOWLEDGED: 2,
    DesignStatus.ASSIGNED: 3,
    DesignStatus.IN_PROGRESS: 4,
    DesignStatus.CORRECTION_REQUIRED: 4,
    DesignStatus.RESUBMITTED: 4,
    DesignStatus.SUBMITTED: 5,
    DesignStatus.UNDER_REVIEW: 5,
    DesignStatus.VERIFICATION_PENDING_ACK: 6,
    DesignStatus.VERIFICATION_PENDING: 6,
    DesignStatus.VERIFICATION_CORRECTION: 7,
    DesignStatus.AWAITING_COMPLIANCE: 7,
    DesignStatus.COMPLIANCE_PENDING_ACK: 8,
    DesignStatus.COMPLIANCE_PENDING: 8,
    DesignStatus.COMPLIANCE_CORRECTION: 9,
    DesignStatus.FINAL_APPROVAL_PENDING: 9,
    DesignStatus.APPROVED: 10,
}

STAGE_ROLE_LABELS = {
    DesignStatus.ENGINEER_PENDING_ACK: ('engineer', 'Awaiting Acknowledgement'),
    DesignStatus.ENGINEER_IN_PROGRESS: ('engineer', 'Site Engineer'),
    DesignStatus.NEW_REQUEST: ('hod', 'Awaiting Acknowledgement'),
    DesignStatus.ACKNOWLEDGED: ('hod', 'Assigning Designer'),
    DesignStatus.ASSIGNED: ('hod', 'Assigning Designer'),
    DesignStatus.IN_PROGRESS: ('designer', 'Designer'),
    DesignStatus.CORRECTION_REQUIRED: ('designer', 'Awaiting Correction'),
    DesignStatus.RESUBMITTED: ('designer', 'Designer'),
    DesignStatus.SUBMITTED: ('hod', 'Submitted'),
    DesignStatus.UNDER_REVIEW: ('hod', 'HOD Review'),
    DesignStatus.VERIFICATION_PENDING_ACK: ('verifier', 'Verifier Ack'),
    DesignStatus.VERIFICATION_PENDING: ('verifier', 'Verifier'),
    DesignStatus.VERIFICATION_CORRECTION: ('hod', 'HOD Review'),
    DesignStatus.AWAITING_COMPLIANCE: ('hod', 'HOD'),
    DesignStatus.COMPLIANCE_PENDING_ACK: ('compliance', 'Compliance Ack'),
    DesignStatus.COMPLIANCE_PENDING: ('compliance', 'Compliance'),
    DesignStatus.COMPLIANCE_CORRECTION: ('hod', 'HOD Review'),
    DesignStatus.FINAL_APPROVAL_PENDING: ('hod', 'Final Approval'),
    DesignStatus.APPROVED: ('hod', 'Approved'),
    DesignStatus.COMPLETED: ('complete', 'Completed'),
}

DELAY_STATUS_LABELS = {
    DesignStatus.ENGINEER_PENDING_ACK: 'Site Engineer — Acknowledgement',
    DesignStatus.ENGINEER_IN_PROGRESS: 'Site Engineer',
    DesignStatus.NEW_REQUEST: 'Head of Design — Acknowledgement',
    DesignStatus.ACKNOWLEDGED: 'Head of Design — Assignment',
    DesignStatus.ASSIGNED: 'Designer — Accept Assignment',
    DesignStatus.IN_PROGRESS: 'Designer',
    DesignStatus.CORRECTION_REQUIRED: 'Designer — Correction',
    DesignStatus.RESUBMITTED: 'Designer — Resubmitted',
    DesignStatus.SUBMITTED: 'Head of Design — Review',
    DesignStatus.UNDER_REVIEW: 'Head of Design — Review',
    DesignStatus.VERIFICATION_PENDING_ACK: 'Verifier — Acknowledgement',
    DesignStatus.VERIFICATION_PENDING: 'Verifier',
    DesignStatus.VERIFICATION_CORRECTION: 'Head of Design — Post-Verification',
    DesignStatus.AWAITING_COMPLIANCE: 'Head of Design — Post-Verification',
    DesignStatus.COMPLIANCE_PENDING_ACK: 'Compliance — Acknowledgement',
    DesignStatus.COMPLIANCE_PENDING: 'Compliance',
    DesignStatus.COMPLIANCE_CORRECTION: 'Head of Design — Post-Compliance',
    DesignStatus.FINAL_APPROVAL_PENDING: 'Head of Design — Final Approval',
    DesignStatus.APPROVED: 'Head of Design — Final Approval',
}


def _days_between(start, end):
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


def _first_assigned_at(design):
    assignment = design.assignments.order_by('assigned_at').first()
    return assignment.assigned_at if assignment else None


def _person_name(user):
    if not user:
        return None
    return user.get_full_name() or user.username


def _is_hod_role(user):
    return bool(user and user.role == UserRole.HEAD_OF_DESIGN)


def _is_admin_only_user(user):
    return bool(user and (user.is_superuser or user.role == UserRole.ADMIN))


def _is_valid_hod_actor(user, *, from_activity_log=False):
    if not user:
        return False
    if from_activity_log:
        return True
    return _is_hod_role(user)


def _latest_hod_activity_user(design):
    log = (
        ActivityLog.objects.filter(
            entity_type='design_request',
            entity_id=design.pk,
            action__in=HOD_ACTIONS,
        )
        .select_related('user')
        .order_by('-created_at')
        .first()
    )
    if log and log.user and _is_valid_hod_actor(log.user, from_activity_log=True):
        return log.user
    return None


def _hod_actor_for_action(design, action):
    log = (
        ActivityLog.objects.filter(
            entity_type='design_request',
            entity_id=design.pk,
            action=action,
        )
        .select_related('user')
        .order_by('-created_at')
        .first()
    )
    if log and log.user and _is_valid_hod_actor(log.user, from_activity_log=True):
        return _person_name(log.user), log.user.id
    return None, None


def _role_key_for_status(status):
    role, _label = STAGE_ROLE_LABELS.get(status, ('hod', ''))
    return role if role != 'complete' else 'hod'


def _is_reminder_target_valid(design, user_id):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return False
    if _is_admin_only_user(user):
        return ActivityLog.objects.filter(
            entity_type='design_request',
            entity_id=design.pk,
            user_id=user_id,
        ).exists()
    return True


def get_hod_name_and_id(design):
    actor = _latest_hod_activity_user(design)
    if actor:
        return _person_name(actor), actor.id

    holder = design.current_holder
    if holder and _is_valid_hod_actor(holder) and _is_hod_role(holder):
        return _person_name(holder), holder.id

    if design.assigned_by and _is_valid_hod_actor(design.assigned_by) and _is_hod_role(design.assigned_by):
        return _person_name(design.assigned_by), design.assigned_by_id

    hod = get_head_of_design()
    if hod and _is_hod_role(hod):
        return _person_name(hod), hod.id

    return None, None


def format_person_display(name, role_label):
    if name and role_label:
        return f'{name} ({role_label})'
    return role_label or name or ''


def _resolve_actor_name(person, role_key, hod_name=None):
    if person:
        return person
    if role_key == 'hod' and hod_name:
        return hod_name
    return None


def _split_delay_stage_label(label):
    if not label:
        return None, None
    if ' — ' in label:
        role, step = label.split(' — ', 1)
        return role.strip(), step.strip()
    return label.strip(), None


def format_delay_waiting_on(person, role_key):
    if person:
        return person
    return ROLE_LABELS.get(role_key, role_key.replace('_', ' ').title())


def _format_days_count(days):
    if days is None:
        return ''
    unit = 'day' if days == 1 else 'days'
    return f'({days:g} {unit})'


def format_delay_target_summary(days_over_target, target_date):
    """Past target row: always requester target_completion_date + days past total target."""
    if days_over_target is None or not target_date:
        return ''
    date_display = target_date.strftime('%d %b %Y')
    return f'deadline {date_display} {_format_days_count(days_over_target)}'


def format_assigned_summary(person, role_key, since_dt, waiting_days):
    role_label = ROLE_LABELS.get(role_key, role_key.replace('_', ' ').title())
    name_part = format_person_display(person, role_label) if person else role_label
    if not since_dt:
        return name_part
    since_str = timezone.localtime(since_dt).strftime('%d %b, %I:%M %p')
    days_part = _format_days_count(waiting_days) if waiting_days is not None else ''
    return f'{name_part} · since {since_str} {days_part}'.strip()


def format_progress_target_summary(target_date, now_time):
    if not target_date:
        return ''
    date_display = target_date.strftime('%d %b %Y')
    target_end = _target_end_datetime(target_date)
    if not target_end:
        return f'deadline {date_display}'
    remaining = _days_between(now_time, target_end)
    if remaining is not None and remaining > 0:
        unit = 'day' if remaining == 1 else 'days'
        return f'deadline {date_display} ({remaining:g} {unit} left)'
    return f'deadline {date_display}'


def format_completed_finished_summary(completion_date):
    if not completion_date:
        return ''
    local_dt = timezone.localtime(completion_date)
    return local_dt.strftime('Finished %d %b %Y, %I:%M %p')


def format_completed_target_on_time_summary(target_date):
    if not target_date:
        return 'Completed on time'
    date_display = target_date.strftime('%d %b %Y')
    return f'deadline {date_display} · on time'


def _resolve_person_waiting_since(design, role_key, fallback_since=None):
    """
    Waiting on row: when the current actor received the task (assignment/ack).
    Uses workflow timestamps — never requester target_completion_date.
    """
    if role_key == 'designer':
        assignment = design.assignments.order_by('-assigned_at').first()
        if assignment:
            return assignment.assigned_at
    if role_key == 'verifier' and design.verification_assigned_at:
        return design.verification_acknowledged_at or design.verification_assigned_at
    if role_key == 'compliance' and design.compliance_assigned_at:
        return design.compliance_acknowledged_at or design.compliance_assigned_at

    waiting_since, _responsible = _waiting_since_for_status(design)
    return waiting_since or fallback_since


def _role_label_for_key(role_key):
    return ROLE_LABELS.get(role_key, role_key.replace('_', ' ').title())


def get_hod_name(design):
    name, _hod_id = get_hod_name_and_id(design)
    return name or ROLE_LABELS['hod']


def _ongoing_stage_duration(design, stage):
    return (
        design.stage_durations.filter(stage=stage, ended_at__isnull=True)
        .order_by('-started_at')
        .first()
    )


def _waiting_since_for_status(design):
    status = design.status
    duration = _ongoing_stage_duration(design, status)
    if duration:
        return duration.started_at, duration.responsible_user

    if status == DesignStatus.NEW_REQUEST:
        return design.created_at, None
    if status == DesignStatus.ACKNOWLEDGED:
        return design.deadline_start or design.created_at, None
    if status == DesignStatus.ASSIGNED:
        return _first_assigned_at(design), design.assigned_designer
    if status in (DesignStatus.IN_PROGRESS, DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED):
        assignment = design.assignments.order_by('-assigned_at').first()
        return (assignment.assigned_at if assignment else design.updated_at), design.assigned_designer
    if status in (DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW):
        submission = design.submissions.order_by('-version_number').first()
        return (submission.submitted_at if submission else design.updated_at), None
    if status == DesignStatus.VERIFICATION_PENDING_ACK:
        return design.verification_assigned_at, design.assigned_verifier
    if status == DesignStatus.VERIFICATION_PENDING:
        return design.verification_acknowledged_at or design.verification_assigned_at, design.assigned_verifier
    if status in (DesignStatus.VERIFICATION_CORRECTION, DesignStatus.AWAITING_COMPLIANCE):
        verification = design.verifications.order_by('-created_at').first()
        return (verification.created_at if verification else design.updated_at), None
    if status == DesignStatus.COMPLIANCE_PENDING_ACK:
        return design.compliance_assigned_at, design.assigned_compliance_officer
    if status == DesignStatus.COMPLIANCE_PENDING:
        return design.compliance_acknowledged_at or design.compliance_assigned_at, design.assigned_compliance_officer
    if status in (DesignStatus.COMPLIANCE_CORRECTION, DesignStatus.FINAL_APPROVAL_PENDING):
        review = design.compliance_reviews.order_by('-created_at').first()
        return (review.created_at if review else design.updated_at), None
    if status == DesignStatus.APPROVED:
        review = design.compliance_reviews.filter(action='approved').order_by('-created_at').first()
        return (review.created_at if review else design.updated_at), None
    return design.updated_at, design.current_holder


def get_current_delay_info(design):
    now_time = timezone.now()
    target_end = _target_end_datetime(design.target_completion_date)
    is_completed = design.status in (DesignStatus.COMPLETED, DesignStatus.CANCELLED)

    if is_completed:
        return None

    waiting_since, responsible = _waiting_since_for_status(design)
    if not waiting_since:
        return None

    elapsed_days = _days_between(waiting_since, now_time) or 0
    is_overdue = bool(target_end and now_time > target_end)
    days_over_target = _days_between(target_end, now_time) if is_overdue else None

    person = _person_name(responsible)
    person_id = responsible.pk if responsible else None
    if not person:
        status = design.status
        if status in (DesignStatus.NEW_REQUEST, DesignStatus.ACKNOWLEDGED, DesignStatus.ASSIGNED,
                      DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW,
                      DesignStatus.VERIFICATION_CORRECTION, DesignStatus.AWAITING_COMPLIANCE,
                      DesignStatus.COMPLIANCE_CORRECTION, DesignStatus.FINAL_APPROVAL_PENDING,
                      DesignStatus.APPROVED):
            person, person_id = get_hod_name_and_id(design)
        elif status in (DesignStatus.IN_PROGRESS, DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED):
            person = _person_name(design.assigned_designer)
            person_id = design.assigned_designer_id
        elif status in (DesignStatus.VERIFICATION_PENDING_ACK, DesignStatus.VERIFICATION_PENDING):
            person = _person_name(design.assigned_verifier)
            person_id = design.assigned_verifier_id
        elif status in (DesignStatus.COMPLIANCE_PENDING_ACK, DesignStatus.COMPLIANCE_PENDING):
            person = _person_name(design.assigned_compliance_officer)
            person_id = design.assigned_compliance_officer_id

    label = DELAY_STATUS_LABELS.get(design.status, design.get_status_display())

    if design.status == DesignStatus.NEW_REQUEST and not design.deadline_start:
        label = 'Head of Design — Acknowledgement'

    from apps.workflow.action_sla import get_action_due_at, is_action_overdue
    action_due_at = get_action_due_at(design)
    is_action_sla_overdue = is_action_overdue(design)

    return {
        'current_stage_label': label,
        'current_person': person,
        'person_id': person_id,
        'waiting_since': waiting_since,
        'elapsed_days': elapsed_days,
        'is_overdue': is_overdue,
        'days_over_target': days_over_target,
        'action_due_at': action_due_at,
        'is_action_sla_overdue': is_action_sla_overdue,
    }


def _label_for_duration(design, stage, counters):
    role, base_label = STAGE_ROLE_LABELS.get(stage, ('hod', stage.replace('_', ' ').title()))

    if stage == DesignStatus.IN_PROGRESS:
        counters['designer'] += 1
        suffix = ' (correction)' if counters['designer'] > 1 else ''
        return 'designer', f'Designer V{counters["designer"]}{suffix}'
    if stage == DesignStatus.RESUBMITTED:
        suffix = ' (correction)' if counters['designer'] > 1 else ''
        return 'designer', f'Designer V{counters["designer"]}{suffix}'
    if stage == DesignStatus.CORRECTION_REQUIRED:
        return 'designer', f'Designer V{counters["designer"] + 1} — awaiting correction'
    if stage == DesignStatus.UNDER_REVIEW:
        counters['hod_review'] += 1
        return 'hod', f'HOD Review (V{counters["hod_review"]})'
    if stage == DesignStatus.VERIFICATION_PENDING:
        counters['verifier'] += 1
        suffix = ' (re-check)' if counters['verifier'] > 1 else ''
        return 'verifier', f'Verifier{suffix}'
    if stage == DesignStatus.VERIFICATION_PENDING_ACK:
        counters['verifier'] += 1
        return 'verifier', f'Verifier Ack'
    if stage == DesignStatus.COMPLIANCE_PENDING:
        counters['compliance'] += 1
        suffix = ' (re-check)' if counters['compliance'] > 1 else ''
        return 'compliance', f'Compliance{suffix}'
    if stage == DesignStatus.COMPLIANCE_PENDING_ACK:
        counters['compliance'] += 1
        return 'compliance', 'Compliance Ack'
    if stage == DesignStatus.VERIFICATION_CORRECTION:
        return 'hod', 'HOD (post-verification)'
    if stage == DesignStatus.COMPLIANCE_CORRECTION:
        return 'hod', 'HOD (post-compliance)'
    if stage == DesignStatus.FINAL_APPROVAL_PENDING:
        return 'hod', 'Final Approval'
    if stage == DesignStatus.APPROVED:
        return 'hod', 'Approved'
    if stage == DesignStatus.COMPLETED:
        return 'complete', 'Completed'

    return role, base_label


def _segments_from_durations(design):
    segments = []
    now_time = timezone.now()
    counters = {'designer': 0, 'hod_review': 0, 'verifier': 0, 'compliance': 0}

    durations = list(design.stage_durations.select_related('responsible_user').order_by('started_at'))
    for duration in durations:
        end = duration.ended_at
        is_ongoing = end is None
        role, label = _label_for_duration(design, duration.stage, counters)
        segments.append({
            'label': label,
            'role': role,
            'person': _person_name(duration.responsible_user),
            'days': _days_between(duration.started_at, end or now_time),
            'is_ongoing': is_ongoing,
            'is_done': not is_ongoing,
            'is_pending': False,
            'is_endcap': False,
            'is_current_delay_source': False,
        })

    return segments


def _synthetic_initial_segment(design):
    now_time = timezone.now()
    if design.status not in (DesignStatus.NEW_REQUEST, DesignStatus.DRAFT):
        return None
    return {
        'label': 'Awaiting Acknowledgement',
        'role': 'hod',
        'person': get_hod_name(design),
        'days': _days_between(design.created_at, now_time),
        'is_ongoing': True,
        'is_done': False,
        'is_pending': False,
        'is_endcap': False,
        'is_current_delay_source': False,
    }


def _append_pending_placeholders(design, segments):
    if design.status in (DesignStatus.COMPLETED, DesignStatus.CANCELLED):
        return

    if design.verification_skipped_by_hod and design.compliance_skipped_by_hod:
        pending_template = [
            ('hod', 'Assign'),
            ('designer', 'Designer'),
            ('hod', 'HOD Review'),
            ('complete', 'Complete'),
        ]
        start_idx = STATUS_PENDING_START.get(design.status, 0)
        if start_idx > 3:
            start_idx = min(start_idx, len(pending_template))
    else:
        pending_template = list(HAPPY_PATH_PENDING)
        start_idx = STATUS_PENDING_START.get(design.status, 0)

    for role, label in pending_template[start_idx:]:
        segments.append({
            'label': label,
            'role': role,
            'person': None,
            'days': None,
            'is_ongoing': False,
            'is_done': False,
            'is_pending': True,
            'is_endcap': role == 'complete',
            'is_current_delay_source': False,
        })


def build_timeline_segments(design):
    segments = _segments_from_durations(design)

    if not segments:
        initial = _synthetic_initial_segment(design)
        if initial:
            segments.append(initial)

    if design.status == DesignStatus.COMPLETED:
        if not segments or not segments[-1].get('is_endcap'):
            segments.append({
                'label': 'Completed',
                'role': 'complete',
                'person': None,
                'days': None,
                'is_ongoing': False,
                'is_done': True,
                'is_pending': False,
                'is_endcap': True,
                'is_current_delay_source': False,
            })
        return segments

    _append_pending_placeholders(design, segments)
    return segments


def _target_marker_percent(design, segments):
    target = design.target_completion_date
    if not target or not segments:
        return None

    requested_at = design.created_at
    overall_end = design.completion_date or timezone.now()
    total_span = (overall_end - requested_at).total_seconds()
    if total_span <= 0:
        return None

    marker_point = _target_start_datetime(target)
    elapsed_to_target = (marker_point - requested_at).total_seconds()
    return round(min(100, max(0, (elapsed_to_target / total_span) * 100)), 1)


def get_lifecycle_timeline_data(design):
    if design.status == DesignStatus.DRAFT:
        return None

    segments = build_timeline_segments(design)
    if not segments:
        return None

    delay_info = get_current_delay_info(design)
    target = design.target_completion_date
    target_end = _target_end_datetime(target)
    now_time = timezone.now()

    is_completed = design.status == DesignStatus.COMPLETED
    is_completed_on_time = bool(
        is_completed and target and design.completion_date
        and design.completion_date.date() <= target
    )
    is_completed_late = bool(
        is_completed and target and design.completion_date
        and design.completion_date.date() > target
    )
    days_late = None
    if is_completed_late and target_end and design.completion_date:
        days_late = _days_between(target_end, design.completion_date)

    if delay_info and delay_info['is_overdue'] and not is_completed:
        for seg in reversed(segments):
            if seg.get('is_ongoing') and not seg.get('is_pending'):
                seg['is_current_delay_source'] = True
                break

    return {
        'segments': segments,
        'delay_info': delay_info,
        'target_date': target,
        'target_marker_percent': _target_marker_percent(design, segments),
        'is_completed_on_time': is_completed_on_time,
        'is_completed_late': is_completed_late,
        'days_late': days_late,
        'historical_delay_stage': design.delay_source or None,
    }


def _review_end_for_submission(design, submission):
    review = design.reviews.filter(
        created_at__gte=submission.submitted_at,
    ).order_by('created_at').first()
    return review.created_at if review else None


def _verification_approved_at(design):
    verification = design.verifications.filter(action='approved').order_by('created_at').first()
    return verification.created_at if verification else None


def _compliance_approved_at(design):
    review = design.compliance_reviews.filter(action='approved').order_by('created_at').first()
    return review.created_at if review else None


def _approved_at(design):
    duration = design.stage_durations.filter(
        stage=DesignStatus.APPROVED,
    ).order_by('started_at').first()
    if duration:
        return duration.started_at
    return _compliance_approved_at(design)


def get_initials(full_name):
    if not full_name:
        return '?'
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _display_stage_label(label):
    mapping = {
        'Ack': 'Acknowledgement',
        'Assign': 'Assignment',
        'HOD': 'HOD Review',
    }
    return mapping.get(label, label)


def _ack_segment_actor(design, hod_name, hod_id):
    if not design.deadline_start:
        return None, None
    person, person_id = _hod_actor_for_action(design, 'acknowledge')
    if person:
        return person, person_id
    return hod_name, hod_id


def _assign_segment_actor(design, hod_name, hod_id):
    if not design.assigned_at:
        return None, None
    person, person_id = _hod_actor_for_action(design, 'assign')
    if person:
        return person, person_id
    if design.assigned_by and _is_hod_role(design.assigned_by):
        return _person_name(design.assigned_by), design.assigned_by_id
    return hod_name, hod_id


def _add_workflow_person(people, user, role_key):
    if not user:
        return
    name = _person_name(user)
    if not name or name in people:
        return
    if role_key == 'hod' and not _is_valid_hod_actor(user):
        return
    role_label = ROLE_LABELS[role_key]
    palette = {
        'hod': ('#B5D4F4', '#042C53'),
        'designer': ('#9FE1CB', '#04342C'),
        'verifier': ('#FAC775', '#412402'),
        'compliance': ('#F4C0D1', '#4B1528'),
    }
    bg, fg = palette.get(role_key, ('#F1F5F9', '#475569'))
    people[name] = {
        'name': name,
        'initials': get_initials(name),
        'bg': bg,
        'fg': fg,
        'role_label': role_label,
        'display_name': format_person_display(name, role_label),
        'user_id': user.pk,
    }


def build_lifecycle_data(design):
    """Build the lifecycle card context object from real workflow timestamps."""
    now_time = timezone.now()
    target_end = _target_end_datetime(design.target_completion_date)
    hod_name, hod_id = get_hod_name_and_id(design)
    ack_person, ack_id = _ack_segment_actor(design, hod_name, hod_id)
    assign_person, assign_id = _assign_segment_actor(design, hod_name, hod_id)

    segments = []
    people = {}

    def add_segment(label, role, person, start, end, note=None, person_id=None):
        if not start:
            return
        is_ongoing = end is None
        days = round(((end or now_time) - start).total_seconds() / 86400, 1)
        segments.append({
            'label': label,
            'role': role,
            'person': person,
            'person_id': person_id,
            'days': days,
            'grow': max(days, 0.3),
            'is_ongoing': is_ongoing,
            'is_delay': False,
            'note': note,
            'start': start,
            'end': end,
        })

    add_segment('Ack', 'hod', ack_person, design.created_at, design.deadline_start, person_id=ack_id)
    add_segment('Assign', 'hod', assign_person, design.deadline_start, design.assigned_at, person_id=assign_id)

    revisions = list(design.submissions.order_by('version_number'))
    prev_end = design.assigned_at
    for rev in revisions:
        designer_name = _person_name(rev.submitted_by)
        note = 'Correction' if rev.version_number > 1 else None
        add_segment(
            f'Designer V{rev.version_number}',
            'designer',
            designer_name,
            prev_end,
            rev.submitted_at,
            note=note,
            person_id=rev.submitted_by_id,
        )
        _add_workflow_person(people, rev.submitted_by, 'designer')
        review_end = _review_end_for_submission(design, rev)
        review_user = _latest_hod_activity_user(design)
        review_person = _person_name(review_user) if review_user else None
        review_person_id = review_user.pk if review_user else None
        add_segment(
            'HOD',
            'hod',
            review_person,
            rev.submitted_at,
            review_end,
            person_id=review_person_id,
        )
        prev_end = review_end or rev.submitted_at

    if not revisions and design.assigned_designer_id and design.assigned_at:
        designer_name = _person_name(design.assigned_designer)
        add_segment(
            'Designer V1',
            'designer',
            designer_name,
            design.assigned_at,
            None,
            person_id=design.assigned_designer_id,
        )
        _add_workflow_person(people, design.assigned_designer, 'designer')

    verification_approved_at = _verification_approved_at(design)
    if design.verification_acknowledged_at:
        verifier_name = _person_name(design.assigned_verifier)
        add_segment(
            'Verifier',
            'verifier',
            verifier_name,
            design.verification_acknowledged_at,
            verification_approved_at,
            person_id=design.assigned_verifier_id,
        )
        _add_workflow_person(people, design.assigned_verifier, 'verifier')
        add_segment(
            'HOD',
            'hod',
            hod_name,
            verification_approved_at,
            design.compliance_assigned_at,
            person_id=hod_id,
        )

    compliance_approved_at = _compliance_approved_at(design)
    if design.compliance_acknowledged_at:
        compliance_name = _person_name(design.assigned_compliance_officer)
        add_segment(
            'Compliance',
            'compliance',
            compliance_name,
            design.compliance_acknowledged_at,
            compliance_approved_at,
            person_id=design.assigned_compliance_officer_id,
        )
        _add_workflow_person(people, design.assigned_compliance_officer, 'compliance')
        add_segment(
            'HOD',
            'hod',
            hod_name,
            compliance_approved_at,
            _approved_at(design),
            person_id=hod_id,
        )

    if design.completion_date:
        segments.append({
            'label': 'Completed',
            'role': 'endcap',
            'person': None,
            'person_id': None,
            'days': None,
            'grow': 0.6,
            'is_ongoing': False,
            'is_delay': False,
            'note': None,
            'start': None,
            'end': None,
        })

    if hod_id:
        hod_user = User.objects.filter(pk=hod_id).first()
        _add_workflow_person(people, hod_user, 'hod')

    for seg in segments:
        if seg.get('label'):
            seg['label'] = _display_stage_label(seg['label'])

    is_overdue = bool(
        target_end and now_time > target_end and not design.completion_date
    )
    delay_stage_label = None
    delay_person = None
    delay_person_id = None
    delay_since = None
    current_stage_label = None
    current_person = None
    current_elapsed_days = None
    current_role_key = None

    for seg in segments:
        if seg.get('is_ongoing'):
            current_stage_label = seg['label']
            current_person = seg['person']
            current_role_key = seg['role']
            current_elapsed_days = seg['days']
            if is_overdue:
                seg['is_delay'] = True
                delay_stage_label = seg['label']
                delay_person = seg['person']
                delay_since = seg['start']
                delay_person_id = seg.get('person_id')
            break

    if not current_stage_label and not design.completion_date:
        delay_info = get_current_delay_info(design)
        if delay_info:
            current_stage_label = delay_info['current_stage_label']
            current_person = delay_info['current_person']
            current_elapsed_days = delay_info['elapsed_days']
            current_role_key = _role_key_for_status(design.status)
            if is_overdue:
                delay_stage_label = delay_info['current_stage_label']
                delay_person = delay_info['current_person']
                delay_since = delay_info['waiting_since']
                delay_person_id = delay_info.get('person_id')
                for seg in reversed(segments):
                    if seg.get('is_ongoing'):
                        seg['is_delay'] = True
                        break

    if is_overdue:
        person_waiting_since = _resolve_person_waiting_since(
            design, current_role_key or 'hod', delay_since,
        )
        if person_waiting_since:
            delay_since = person_waiting_since

    def _resolve_display(person, role_key, person_id=None):
        role_label = ROLE_LABELS.get(role_key, role_key)
        if person:
            return format_person_display(person, role_label), person_id
        if role_key == 'hod' and hod_name:
            return format_person_display(hod_name, role_label), hod_id
        return role_label, person_id

    current_person_display, _ = _resolve_display(
        current_person, current_role_key or 'hod',
    )
    delay_person_display, delay_person_id = _resolve_display(
        delay_person,
        current_role_key or 'hod',
        delay_person_id,
    )

    if delay_person_id and not _is_reminder_target_valid(design, delay_person_id):
        delay_person_id = None

    total_days = None
    if design.created_at:
        total_days = round(
            ((design.completion_date or now_time) - design.created_at).total_seconds() / 86400,
            1,
        )

    days_allowed = None
    if target_end and design.created_at:
        days_allowed = _days_between(design.created_at, target_end)

    days_over_target = None
    if target_end:
        if is_overdue:
            days_over_target = _days_between(target_end, now_time)
        elif design.completion_date and design.completion_date > target_end:
            days_over_target = _days_between(target_end, design.completion_date)

    is_completed_on_time = bool(
        design.completion_date and design.target_completion_date
        and design.completion_date.date() <= design.target_completion_date
    )
    days_late = days_over_target if (design.completion_date and not is_completed_on_time) else None

    if design.completion_date and not is_completed_on_time and not delay_stage_label:
        delay_stage_label = design.delay_source or 'Unknown stage'

    delay_stage_role, delay_stage_step = _split_delay_stage_label(delay_stage_label)
    delay_waiting_on = (
        format_delay_waiting_on(
            _resolve_actor_name(delay_person, current_role_key or 'hod', hod_name),
            current_role_key or 'hod',
        )
        if is_overdue else None
    )
    delay_waiting_days = (
        _days_between(delay_since, now_time) if is_overdue and delay_since else None
    )
    delay_waiting_days_display = _format_days_count(delay_waiting_days) if is_overdue else None
    # Past target: requester target only — independent of delay_waiting_days (person hold time).
    delay_target_summary = (
        format_delay_target_summary(days_over_target, design.target_completion_date)
        if is_overdue else None
    )
    current_waiting_on = format_delay_waiting_on(
        current_person, current_role_key or 'hod',
    )

    progress_assigned_summary = None
    progress_target_summary = None
    completed_finished_summary = None
    completed_target_summary = None
    completed_late_target_summary = None

    if not design.completion_date and not is_overdue:
        progress_role_key = current_role_key or 'hod'
        progress_since = _resolve_person_waiting_since(design, progress_role_key, None)
        progress_waiting_days = (
            _days_between(progress_since, now_time) if progress_since else None
        )
        progress_assigned_summary = format_assigned_summary(
            _resolve_actor_name(current_person, progress_role_key, hod_name),
            progress_role_key,
            progress_since,
            progress_waiting_days,
        )
        progress_target_summary = format_progress_target_summary(
            design.target_completion_date, now_time,
        )

    if is_completed_on_time:
        completed_finished_summary = format_completed_finished_summary(design.completion_date)
        completed_target_summary = format_completed_target_on_time_summary(
            design.target_completion_date,
        )

    if design.completion_date and not is_completed_on_time:
        completed_late_target_summary = format_delay_target_summary(
            days_late, design.target_completion_date,
        )

    target_marker_percent = None
    if design.target_completion_date and design.created_at and segments:
        overall_end = design.completion_date or now_time
        total_span = (overall_end - design.created_at).total_seconds()
        if total_span > 0:
            marker_point = _target_start_datetime(design.target_completion_date)
            elapsed_to_target = (marker_point - design.created_at).total_seconds()
            target_marker_percent = round(
                min(100, max(0, (elapsed_to_target / total_span) * 100)),
                1,
            )

    return {
        'segments': segments,
        'people': list(people.values()),
        'total_days': total_days,
        'days_allowed': days_allowed,
        'is_overdue': is_overdue,
        'is_completed_on_time': is_completed_on_time,
        'days_over_target': days_over_target,
        'days_late': days_late,
        'current_stage_label': current_stage_label,
        'current_person': current_person,
        'current_person_display': current_person_display,
        'current_elapsed_days': current_elapsed_days,
        'delay_stage_label': delay_stage_label,
        'delay_stage_role': delay_stage_role,
        'delay_stage_step': delay_stage_step,
        'delay_person': delay_person,
        'delay_person_display': delay_person_display,
        'delay_waiting_on': delay_waiting_on,
        'delay_waiting_days': delay_waiting_days,
        'delay_waiting_days_display': delay_waiting_days_display,
        'delay_target_summary': delay_target_summary,
        'delay_person_id': delay_person_id,
        'delay_since': delay_since,
        'current_waiting_on': current_waiting_on,
        'progress_assigned_summary': progress_assigned_summary,
        'progress_target_summary': progress_target_summary,
        'completed_finished_summary': completed_finished_summary,
        'completed_target_summary': completed_target_summary,
        'completed_late_target_summary': completed_late_target_summary,
        'target_marker_percent': target_marker_percent,
    }
