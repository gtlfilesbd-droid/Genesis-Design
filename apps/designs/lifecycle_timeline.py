from datetime import datetime, time

from django.utils import timezone

from apps.accounts.models import UserRole
from apps.core.models import ActivityLog
from apps.designs.models import DesignStatus
from apps.workflow.services import get_head_of_design

HAPPY_PATH_PENDING = [
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
    DesignStatus.NEW_REQUEST: 0,
    DesignStatus.ACKNOWLEDGED: 1,
    DesignStatus.ASSIGNED: 2,
    DesignStatus.IN_PROGRESS: 3,
    DesignStatus.CORRECTION_REQUIRED: 3,
    DesignStatus.RESUBMITTED: 3,
    DesignStatus.SUBMITTED: 4,
    DesignStatus.UNDER_REVIEW: 4,
    DesignStatus.VERIFICATION_PENDING_ACK: 5,
    DesignStatus.VERIFICATION_PENDING: 5,
    DesignStatus.VERIFICATION_CORRECTION: 6,
    DesignStatus.AWAITING_COMPLIANCE: 6,
    DesignStatus.COMPLIANCE_PENDING_ACK: 7,
    DesignStatus.COMPLIANCE_PENDING: 7,
    DesignStatus.COMPLIANCE_CORRECTION: 8,
    DesignStatus.FINAL_APPROVAL_PENDING: 8,
    DesignStatus.APPROVED: 9,
}

STAGE_ROLE_LABELS = {
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


def get_hod_name(design):
    hod_actions = (
        'acknowledge', 'assign', 'request_correction', 'accept_design',
        'send_to_verification', 'forward_to_designer', 'send_to_compliance',
        'compliance_approved', 'complete', 'hod_fast_complete', 'start_review',
    )
    log = (
        ActivityLog.objects.filter(
            entity_type='design_request',
            entity_id=design.pk,
            action__in=hod_actions,
        )
        .select_related('user')
        .order_by('-created_at')
        .first()
    )
    if log and log.user:
        return _person_name(log.user)
    if design.assigned_by:
        return _person_name(design.assigned_by)
    hod = get_head_of_design()
    return _person_name(hod) or 'Head of Design'


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
    if not person:
        status = design.status
        if status in (DesignStatus.NEW_REQUEST, DesignStatus.ACKNOWLEDGED, DesignStatus.ASSIGNED,
                      DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW,
                      DesignStatus.VERIFICATION_CORRECTION, DesignStatus.AWAITING_COMPLIANCE,
                      DesignStatus.COMPLIANCE_CORRECTION, DesignStatus.FINAL_APPROVAL_PENDING,
                      DesignStatus.APPROVED):
            person = get_hod_name(design)
        elif status in (DesignStatus.IN_PROGRESS, DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED):
            person = _person_name(design.assigned_designer)
        elif status in (DesignStatus.VERIFICATION_PENDING_ACK, DesignStatus.VERIFICATION_PENDING):
            person = _person_name(design.assigned_verifier)
        elif status in (DesignStatus.COMPLIANCE_PENDING_ACK, DesignStatus.COMPLIANCE_PENDING):
            person = _person_name(design.assigned_compliance_officer)

    label = DELAY_STATUS_LABELS.get(design.status, design.get_status_display())

    if design.status == DesignStatus.NEW_REQUEST and not design.deadline_start:
        label = 'Head of Design — Acknowledgement'

    return {
        'current_stage_label': label,
        'current_person': person,
        'waiting_since': waiting_since,
        'elapsed_days': elapsed_days,
        'is_overdue': is_overdue,
        'days_over_target': days_over_target,
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


def get_hod_name_and_id(design):
    from apps.notifications.services import NotificationService

    users = NotificationService._project_users(design.project, 'PROJECT_PERM_ASSIGN')
    hod = users[0] if users else get_head_of_design()
    if hod:
        return hod.get_full_name() or hod.username, hod.id
    return 'Head of Design', None


ROLE_LABELS = {
    'hod': 'Head of Design',
    'designer': 'Designer',
    'verifier': 'Verifier',
    'compliance': 'Compliance',
}


def _display_stage_label(label):
    mapping = {
        'Ack': 'Acknowledgement',
        'Assign': 'Assignment',
        'HOD': 'HOD Review',
    }
    return mapping.get(label, label)


def build_lifecycle_data(design):
    """Build the lifecycle card context object from real workflow timestamps."""
    now_time = timezone.now()
    target_end = _target_end_datetime(design.target_completion_date)
    hod_name, hod_id = get_hod_name_and_id(design)

    segments = []
    people = {}

    def add_person(name, role_key, role_label, user_id=None):
        if not name or name in people:
            return
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
            'user_id': user_id,
        }

    def add_segment(label, role, person, start, end, note=None):
        if not start:
            return
        is_ongoing = end is None
        days = round(((end or now_time) - start).total_seconds() / 86400, 1)
        segments.append({
            'label': label,
            'role': role,
            'person': person,
            'days': days,
            'grow': max(days, 0.3),
            'is_ongoing': is_ongoing,
            'is_delay': False,
            'note': note,
            'start': start,
            'end': end,
        })

    add_segment('Ack', 'hod', hod_name, design.created_at, design.deadline_start)
    add_segment('Assign', 'hod', hod_name, design.deadline_start, design.assigned_at)

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
        )
        if designer_name:
            add_person(designer_name, 'designer', ROLE_LABELS['designer'], rev.submitted_by_id)
        review_end = _review_end_for_submission(design, rev)
        add_segment('HOD', 'hod', hod_name, rev.submitted_at, review_end)
        prev_end = review_end or rev.submitted_at

    if not revisions and design.assigned_designer_id and design.assigned_at:
        designer_name = _person_name(design.assigned_designer)
        add_segment('Designer V1', 'designer', designer_name, design.assigned_at, None)
        if designer_name:
            add_person(designer_name, 'designer', ROLE_LABELS['designer'], design.assigned_designer_id)

    verification_approved_at = _verification_approved_at(design)
    if design.verification_acknowledged_at:
        verifier_name = _person_name(design.assigned_verifier)
        add_segment(
            'Verifier',
            'verifier',
            verifier_name,
            design.verification_acknowledged_at,
            verification_approved_at,
        )
        if verifier_name:
            add_person(verifier_name, 'verifier', ROLE_LABELS['verifier'], design.assigned_verifier_id)
        add_segment(
            'HOD',
            'hod',
            hod_name,
            verification_approved_at,
            design.compliance_assigned_at,
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
        )
        if compliance_name:
            add_person(
                compliance_name,
                'compliance',
                ROLE_LABELS['compliance'],
                design.assigned_compliance_officer_id,
            )
        add_segment(
            'HOD',
            'hod',
            hod_name,
            compliance_approved_at,
            _approved_at(design),
        )

    if design.completion_date:
        segments.append({
            'label': 'Completed',
            'role': 'endcap',
            'person': None,
            'days': None,
            'grow': 0.6,
            'is_ongoing': False,
            'is_delay': False,
            'note': None,
            'start': None,
            'end': None,
        })

    add_person(hod_name, 'hod', ROLE_LABELS['hod'], hod_id)

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

    for seg in segments:
        if seg.get('is_ongoing'):
            current_stage_label = seg['label']
            current_person = seg['person']
            current_elapsed_days = seg['days']
            if is_overdue:
                seg['is_delay'] = True
                delay_stage_label = seg['label']
                delay_person = seg['person']
                delay_since = seg['start']
                person_obj = people.get(seg['person']) if seg['person'] else None
                delay_person_id = person_obj['user_id'] if person_obj else None
            break

    if not current_stage_label and not design.completion_date:
        delay_info = get_current_delay_info(design)
        if delay_info:
            current_stage_label = delay_info['current_stage_label']
            current_person = delay_info['current_person']
            current_elapsed_days = delay_info['elapsed_days']
            if is_overdue:
                delay_stage_label = delay_info['current_stage_label']
                delay_person = delay_info['current_person']
                delay_since = delay_info['waiting_since']
                for seg in reversed(segments):
                    if seg.get('is_ongoing'):
                        seg['is_delay'] = True
                        break
                if delay_person:
                    person_obj = people.get(delay_person)
                    if not person_obj and design.assigned_designer:
                        delay_person_id = design.assigned_designer_id
                    elif person_obj:
                        delay_person_id = person_obj['user_id']
                    elif hod_id:
                        delay_person_id = hod_id

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
        'current_elapsed_days': current_elapsed_days,
        'delay_stage_label': delay_stage_label,
        'delay_person': delay_person,
        'delay_person_id': delay_person_id,
        'delay_since': delay_since,
        'target_marker_percent': target_marker_percent,
    }
