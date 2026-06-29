from datetime import timedelta

from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from apps.designs.models import (
    ComplianceReview,
    DesignAssignment,
    DesignRequest,
    DesignStatus,
    DesignSubmission,
    Verification,
)
from apps.workflow.deadline_utils import add_allowed_duration, get_deadline_config

ACTION_SLA_CONFIG = {
    DesignStatus.ENGINEER_PENDING_ACK: 'action_engineer_acknowledge',
    DesignStatus.NEW_REQUEST: 'action_acknowledge',
    DesignStatus.ACKNOWLEDGED: 'action_assign_designer',
    DesignStatus.ASSIGNED: 'action_accept_assignment',
    DesignStatus.SUBMITTED: 'action_hod_review',
    DesignStatus.UNDER_REVIEW: 'action_hod_review',
    DesignStatus.VERIFICATION_CORRECTION: 'action_send_to_verification',
    DesignStatus.VERIFICATION_PENDING_ACK: 'action_verification_ack',
    DesignStatus.AWAITING_COMPLIANCE: 'action_send_to_compliance',
    DesignStatus.COMPLIANCE_PENDING_ACK: 'action_compliance_ack',
    DesignStatus.COMPLIANCE_CORRECTION: 'action_compliance_correction',
    DesignStatus.APPROVED: 'action_mark_complete',
}

ACTION_SLA_STATUSES = frozenset(ACTION_SLA_CONFIG.keys())

HOD_ACTION_STATUSES = frozenset({
    DesignStatus.NEW_REQUEST,
    DesignStatus.ACKNOWLEDGED,
    DesignStatus.SUBMITTED,
    DesignStatus.UNDER_REVIEW,
    DesignStatus.VERIFICATION_CORRECTION,
    DesignStatus.AWAITING_COMPLIANCE,
    DesignStatus.COMPLIANCE_CORRECTION,
    DesignStatus.APPROVED,
    DesignStatus.FINAL_APPROVAL_PENDING,
})

ACTION_DUE_LABELS = {
    DesignStatus.ENGINEER_PENDING_ACK: 'Ack due',
    DesignStatus.NEW_REQUEST: 'Ack due',
    DesignStatus.ACKNOWLEDGED: 'Assign due',
    DesignStatus.ASSIGNED: 'Accept due',
    DesignStatus.SUBMITTED: 'Review due',
    DesignStatus.UNDER_REVIEW: 'Review due',
    DesignStatus.VERIFICATION_CORRECTION: 'Send due',
    DesignStatus.VERIFICATION_PENDING_ACK: 'Ack due',
    DesignStatus.AWAITING_COMPLIANCE: 'Send due',
    DesignStatus.COMPLIANCE_PENDING_ACK: 'Ack due',
    DesignStatus.COMPLIANCE_CORRECTION: 'Forward due',
    DesignStatus.APPROVED: 'Complete due',
}


def get_action_config():
    return get_deadline_config()


def get_action_sla_duration(status, config=None):
    prefix = ACTION_SLA_CONFIG.get(status)
    if not prefix:
        return None
    config = config or get_action_config()
    days = getattr(config, f'{prefix}_days', 0) or 0
    hours = getattr(config, f'{prefix}_hours', 0) or 0
    return timedelta(days=days, hours=hours)


def _latest_assignment_at(design):
    assignment = design.assignments.order_by('-assigned_at').first()
    return assignment.assigned_at if assignment else None


def _latest_submission_at(design):
    submission = design.submissions.order_by('-version_number').first()
    return submission.submitted_at if submission else None


def _verification_correction_at(design):
    row = design.verifications.filter(action='correction').order_by('-created_at').first()
    return row.created_at if row else None


def _verification_approved_at(design):
    row = design.verifications.filter(action='approved').order_by('-created_at').first()
    return row.created_at if row else None


def _compliance_correction_at(design):
    row = design.compliance_reviews.filter(action='correction').order_by('-created_at').first()
    return row.created_at if row else None


def _compliance_approved_at(design):
    row = design.compliance_reviews.filter(action='approved').order_by('-created_at').first()
    return row.created_at if row else None


def get_action_anchor(design):
    status = design.status
    if status == DesignStatus.ENGINEER_PENDING_ACK:
        return design.engineer_assigned_at or design.created_at
    if status == DesignStatus.NEW_REQUEST:
        return design.created_at
    if status == DesignStatus.ACKNOWLEDGED:
        return design.deadline_start or design.created_at
    if status == DesignStatus.ASSIGNED:
        return design.assigned_at or _latest_assignment_at(design)
    if status in (DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW):
        return _latest_submission_at(design) or design.updated_at
    if status == DesignStatus.VERIFICATION_CORRECTION:
        return _verification_correction_at(design) or design.updated_at
    if status == DesignStatus.VERIFICATION_PENDING_ACK:
        return design.verification_assigned_at
    if status == DesignStatus.AWAITING_COMPLIANCE:
        return _verification_approved_at(design) or design.updated_at
    if status == DesignStatus.COMPLIANCE_PENDING_ACK:
        return design.compliance_assigned_at
    if status == DesignStatus.COMPLIANCE_CORRECTION:
        return _compliance_correction_at(design) or design.updated_at
    if status == DesignStatus.APPROVED:
        return _compliance_approved_at(design) or design.updated_at
    return None


def compute_action_due_at(anchor, status, config=None):
    if not anchor:
        return None
    duration = get_action_sla_duration(status, config)
    if not duration:
        return None
    config = config or get_action_config()
    return add_allowed_duration(
        anchor,
        duration.days,
        duration.seconds // 3600,
        count_weekends=config.count_weekends,
    )


def get_action_due_at(design, config=None):
    anchor = get_action_anchor(design)
    return compute_action_due_at(anchor, design.status, config)


def is_action_overdue(design, now=None, config=None):
    now = now or timezone.now()
    due = get_action_due_at(design, config)
    return due is not None and now > due


def _hod_is_responsible(design, user):
    return design.current_holder_id == user.pk


def _designer_is_responsible(design, user):
    return design.assigned_designer_id == user.pk


def _verifier_is_responsible(design, user):
    return design.assigned_verifier_id == user.pk


def _compliance_is_responsible(design, user):
    return design.assigned_compliance_officer_id == user.pk


def _engineer_is_responsible(design, user):
    return design.assigned_site_engineer_id == user.pk


def is_action_responsible_user(design, user):
    status = design.status
    if status in HOD_ACTION_STATUSES:
        return _hod_is_responsible(design, user)
    if status == DesignStatus.ENGINEER_PENDING_ACK:
        return _engineer_is_responsible(design, user)
    if status == DesignStatus.ASSIGNED:
        return _designer_is_responsible(design, user)
    if status == DesignStatus.VERIFICATION_PENDING_ACK:
        return _verifier_is_responsible(design, user)
    if status == DesignStatus.COMPLIANCE_PENDING_ACK:
        return _compliance_is_responsible(design, user)
    return False


def is_action_overdue_for_user(design, user, now=None, config=None):
    return is_action_overdue(design, now, config) and is_action_responsible_user(design, user)


def get_action_due_label(design):
    return ACTION_DUE_LABELS.get(design.status, 'Action due')


def _cutoff_for_status(status, now, config):
    duration = get_action_sla_duration(status, config)
    if not duration:
        return None
    return now - duration


def _hod_action_overdue_q(user, now, config=None):
    config = config or get_action_config()
    parts = []
    ack_cutoff = _cutoff_for_status(DesignStatus.NEW_REQUEST, now, config)
    if ack_cutoff:
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.NEW_REQUEST,
            created_at__lt=ack_cutoff,
        ))
    assign_cutoff = _cutoff_for_status(DesignStatus.ACKNOWLEDGED, now, config)
    if assign_cutoff:
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.ACKNOWLEDGED,
            deadline_start__lt=assign_cutoff,
        ))
    review_cutoff = _cutoff_for_status(DesignStatus.SUBMITTED, now, config)
    if review_cutoff:
        latest_sub = DesignSubmission.objects.filter(
            design=OuterRef('pk'),
        ).order_by('-version_number').values('submitted_at')[:1]
        parts.append(Q(
            current_holder=user,
            status__in=[DesignStatus.SUBMITTED, DesignStatus.UNDER_REVIEW],
        ) & Q(pk__in=DesignRequest.objects.annotate(
            latest_submitted_at=Subquery(latest_sub),
        ).filter(
            latest_submitted_at__lt=review_cutoff,
        ).values('pk')))
    verify_resend_cutoff = _cutoff_for_status(DesignStatus.VERIFICATION_CORRECTION, now, config)
    if verify_resend_cutoff:
        latest_ver_corr = Verification.objects.filter(
            design=OuterRef('pk'),
            action='correction',
        ).order_by('-created_at').values('created_at')[:1]
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.VERIFICATION_CORRECTION,
        ) & Q(pk__in=DesignRequest.objects.annotate(
            ver_corr_at=Subquery(latest_ver_corr),
        ).filter(ver_corr_at__lt=verify_resend_cutoff).values('pk')))
    send_comp_cutoff = _cutoff_for_status(DesignStatus.AWAITING_COMPLIANCE, now, config)
    if send_comp_cutoff:
        latest_ver_app = Verification.objects.filter(
            design=OuterRef('pk'),
            action='approved',
        ).order_by('-created_at').values('created_at')[:1]
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.AWAITING_COMPLIANCE,
        ) & Q(pk__in=DesignRequest.objects.annotate(
            ver_app_at=Subquery(latest_ver_app),
        ).filter(ver_app_at__lt=send_comp_cutoff).values('pk')))
    comp_corr_cutoff = _cutoff_for_status(DesignStatus.COMPLIANCE_CORRECTION, now, config)
    if comp_corr_cutoff:
        latest_comp_corr = ComplianceReview.objects.filter(
            design=OuterRef('pk'),
            action='correction',
        ).order_by('-created_at').values('created_at')[:1]
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.COMPLIANCE_CORRECTION,
        ) & Q(pk__in=DesignRequest.objects.annotate(
            comp_corr_at=Subquery(latest_comp_corr),
        ).filter(comp_corr_at__lt=comp_corr_cutoff).values('pk')))
    complete_cutoff = _cutoff_for_status(DesignStatus.APPROVED, now, config)
    if complete_cutoff:
        latest_comp_app = ComplianceReview.objects.filter(
            design=OuterRef('pk'),
            action='approved',
        ).order_by('-created_at').values('created_at')[:1]
        parts.append(Q(
            current_holder=user,
            status=DesignStatus.APPROVED,
        ) & Q(pk__in=DesignRequest.objects.annotate(
            comp_app_at=Subquery(latest_comp_app),
        ).filter(comp_app_at__lt=complete_cutoff).values('pk')))
    if not parts:
        return Q(pk__in=[])
    combined = parts[0]
    for part in parts[1:]:
        combined |= part
    return combined


def _designer_action_overdue_q(user, now, config=None):
    config = config or get_action_config()
    cutoff = _cutoff_for_status(DesignStatus.ASSIGNED, now, config)
    if not cutoff:
        return Q(pk__in=[])
    return Q(
        assigned_designer=user,
        status=DesignStatus.ASSIGNED,
        assignments__assigned_at__lt=cutoff,
    )


def _verification_action_overdue_q(now, config=None):
    config = config or get_action_config()
    cutoff = _cutoff_for_status(DesignStatus.VERIFICATION_PENDING_ACK, now, config)
    if not cutoff:
        return Q(pk__in=[])
    return Q(
        status=DesignStatus.VERIFICATION_PENDING_ACK,
        verification_assigned_at__lt=cutoff,
    )


def _compliance_action_overdue_q(now, config=None):
    config = config or get_action_config()
    cutoff = _cutoff_for_status(DesignStatus.COMPLIANCE_PENDING_ACK, now, config)
    if not cutoff:
        return Q(pk__in=[])
    return Q(
        status=DesignStatus.COMPLIANCE_PENDING_ACK,
        compliance_assigned_at__lt=cutoff,
    )


def _engineer_action_overdue_q(now, config=None):
    config = config or get_action_config()
    cutoff = _cutoff_for_status(DesignStatus.ENGINEER_PENDING_ACK, now, config)
    if not cutoff:
        return Q(pk__in=[])
    return Q(
        status=DesignStatus.ENGINEER_PENDING_ACK,
        engineer_assigned_at__lt=cutoff,
    )


def _engineer_work_overdue_q(now):
    return Q(
        status__in=[
            DesignStatus.ENGINEER_PENDING_ACK,
            DesignStatus.ENGINEER_IN_PROGRESS,
        ],
        engineer_due_date__isnull=False,
        engineer_due_date__lt=now,
    )


def _engineer_overdue_q(now, config=None):
    return _engineer_action_overdue_q(now, config) | _engineer_work_overdue_q(now)


def reset_action_sla_breach(design):
    design.action_sla_breach_status = ''
    design.action_sla_breached_at = None


def mark_action_sla_breach_if_needed(design, now=None):
    now = now or timezone.now()
    if not is_action_overdue(design, now):
        return False
    if design.action_sla_breach_status == design.status and design.action_sla_breached_at:
        return False
    design.action_sla_breach_status = design.status
    design.action_sla_breached_at = now
    design.save(update_fields=['action_sla_breach_status', 'action_sla_breached_at'])
    return True
