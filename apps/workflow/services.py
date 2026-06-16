from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.core.middleware import log_audit
from apps.core.models import StageDuration
from apps.core.utils import log_activity
from apps.designs.models import (
    ComplianceReview, DesignAssignment, DesignRequest, DesignReview, DesignStatus,
    DesignSubmission, DeadlineRecord, DeadlineStatus, Verification,
)

WORKFLOW_ACTIONS = {
    'submit_request': {
        'from': [DesignStatus.DRAFT],
        'to': DesignStatus.NEW_REQUEST,
        'roles': [UserRole.DESIGN_REQUESTER, UserRole.ADMIN],
    },
    'acknowledge': {
        'from': [DesignStatus.NEW_REQUEST],
        'to': DesignStatus.ACKNOWLEDGED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'assign': {
        'from': [
            DesignStatus.ACKNOWLEDGED,
            DesignStatus.VERIFICATION_CORRECTION,
            DesignStatus.COMPLIANCE_CORRECTION,
        ],
        'to': DesignStatus.ASSIGNED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'accept_assignment': {
        'from': [DesignStatus.ASSIGNED],
        'to': DesignStatus.IN_PROGRESS,
        'roles': [UserRole.DESIGNER, UserRole.ADMIN],
    },
    'submit_work': {
        'from': [DesignStatus.IN_PROGRESS, DesignStatus.RESUBMITTED],
        'to': DesignStatus.SUBMITTED,
        'roles': [UserRole.DESIGNER, UserRole.ADMIN],
    },
    'start_review': {
        'from': [DesignStatus.SUBMITTED],
        'to': DesignStatus.UNDER_REVIEW,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
        'auto': True,
    },
    'request_correction': {
        'from': [DesignStatus.UNDER_REVIEW, DesignStatus.SUBMITTED],
        'to': DesignStatus.CORRECTION_REQUIRED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'resubmit': {
        'from': [DesignStatus.CORRECTION_REQUIRED],
        'to': DesignStatus.RESUBMITTED,
        'roles': [UserRole.DESIGNER, UserRole.ADMIN],
    },
    'send_to_verification': {
        'from': [
            DesignStatus.UNDER_REVIEW,
            DesignStatus.SUBMITTED,
            DesignStatus.VERIFICATION_CORRECTION,
        ],
        'to': DesignStatus.VERIFICATION_PENDING,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'accept_design': {
        'from': [DesignStatus.UNDER_REVIEW, DesignStatus.SUBMITTED],
        'to': DesignStatus.VERIFICATION_PENDING,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'verification_correction': {
        'from': [DesignStatus.VERIFICATION_PENDING],
        'to': DesignStatus.VERIFICATION_CORRECTION,
        'roles': [UserRole.VERIFICATION_TEAM, UserRole.ADMIN],
    },
    'verify_approved': {
        'from': [DesignStatus.VERIFICATION_PENDING],
        'to': DesignStatus.AWAITING_COMPLIANCE,
        'roles': [UserRole.VERIFICATION_TEAM, UserRole.ADMIN],
    },
    'send_to_compliance': {
        'from': [
            DesignStatus.AWAITING_COMPLIANCE,
            DesignStatus.COMPLIANCE_CORRECTION,
        ],
        'to': DesignStatus.COMPLIANCE_PENDING,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'compliance_correction': {
        'from': [DesignStatus.COMPLIANCE_PENDING],
        'to': DesignStatus.COMPLIANCE_CORRECTION,
        'roles': [UserRole.COMPLIANCE_TEAM, UserRole.ADMIN],
    },
    'compliance_approved': {
        'from': [DesignStatus.COMPLIANCE_PENDING],
        'to': DesignStatus.APPROVED,
        'roles': [UserRole.COMPLIANCE_TEAM, UserRole.ADMIN],
    },
    'forward_to_designer': {
        'from': [DesignStatus.VERIFICATION_CORRECTION, DesignStatus.COMPLIANCE_CORRECTION],
        'to': DesignStatus.CORRECTION_REQUIRED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'hod_fast_complete': {
        'from': [
            DesignStatus.UNDER_REVIEW,
            DesignStatus.SUBMITTED,
            DesignStatus.VERIFICATION_PENDING,
            DesignStatus.VERIFICATION_CORRECTION,
            DesignStatus.AWAITING_COMPLIANCE,
            DesignStatus.COMPLIANCE_PENDING,
            DesignStatus.COMPLIANCE_CORRECTION,
            DesignStatus.APPROVED,
        ],
        'to': DesignStatus.COMPLETED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'complete': {
        'from': [DesignStatus.APPROVED],
        'to': DesignStatus.COMPLETED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
    'cancel': {
        'from': list(DesignStatus.values),
        'to': DesignStatus.CANCELLED,
        'roles': [UserRole.HEAD_OF_DESIGN, UserRole.ADMIN],
    },
}

_CORRECTION_FROM_STATES = frozenset({
    DesignStatus.VERIFICATION_CORRECTION,
    DesignStatus.COMPLIANCE_CORRECTION,
})


class WorkflowError(Exception):
    pass


def get_head_of_design():
    return User.objects.filter(
        role=UserRole.HEAD_OF_DESIGN, is_active=True, status='active',
    ).first()


def get_verification_team():
    return User.objects.filter(
        role=UserRole.VERIFICATION_TEAM, is_active=True, status='active',
    )


def get_compliance_team():
    return User.objects.filter(
        role=UserRole.COMPLIANCE_TEAM, is_active=True, status='active',
    )


def _check_permission(user, action_config):
    if user.is_superuser or user.role == UserRole.ADMIN:
        return True
    return user.role in action_config['roles']


def _end_stage(design, stage):
    StageDuration.objects.filter(
        design=design, stage=stage, ended_at__isnull=True,
    ).update(ended_at=timezone.now())


def _start_stage(design, stage, user):
    StageDuration.objects.create(
        design=design,
        stage=stage,
        started_at=timezone.now(),
        responsible_user=user,
    )


def _start_deadline(design):
    from apps.workflow.deadline_utils import add_allowed_duration, get_deadline_config

    drawing_type = design.drawing_type
    config = get_deadline_config()
    now = timezone.now()
    due = add_allowed_duration(
        now,
        drawing_type.allowed_days,
        drawing_type.allowed_hours,
        count_weekends=config.count_weekends,
    )
    design.deadline_start = now
    design.deadline_due = due
    design.deadline_status = DeadlineStatus.GREEN
    DeadlineRecord.objects.update_or_create(
        design=design,
        defaults={
            'started_at': now,
            'due_at': due,
            'status': DeadlineStatus.GREEN,
            'warning_notified_at': None,
            'breach_notified_at': None,
            'breached_at': None,
            'escalation_level': 0,
        },
    )


def update_deadline_status(design):
    from apps.notifications.models import NotificationSetting
    from apps.notifications.services import notify_deadline_breach, notify_deadline_warning
    from apps.workflow.deadline_utils import get_deadline_config, warning_threshold_ratio

    if not design.deadline_due:
        return
    config = get_deadline_config()
    notif_settings = NotificationSetting.get_solo()
    now = timezone.now()
    remaining = (design.deadline_due - now).total_seconds()
    total = (
        (design.deadline_due - design.deadline_start).total_seconds()
        if design.deadline_start else 1
    )
    warning_ratio = warning_threshold_ratio(config)

    if remaining <= 0:
        design.deadline_status = DeadlineStatus.RED
    elif remaining / total <= warning_ratio:
        design.deadline_status = DeadlineStatus.YELLOW
    else:
        design.deadline_status = DeadlineStatus.GREEN

    design.deadline_missed = design.deadline_status == DeadlineStatus.RED
    design.save(update_fields=['deadline_status', 'deadline_missed'])

    if not hasattr(design, 'deadline_record'):
        return

    record = design.deadline_record
    record.status = design.deadline_status

    if design.deadline_status == DeadlineStatus.RED and not record.breached_at:
        record.breached_at = now
        if config.auto_breach_notify and not record.breach_notified_at:
            notify_deadline_breach(design)
            record.breach_notified_at = now

    warning_window = timedelta(hours=notif_settings.deadline_warning_hours).total_seconds()
    if (
        remaining > 0
        and remaining <= warning_window
        and not record.warning_notified_at
        and design.deadline_status in (DeadlineStatus.GREEN, DeadlineStatus.YELLOW)
    ):
        notify_deadline_warning(design)
        record.warning_notified_at = now

    record.save()


def _update_latest_submission(design, **fields):
    submission = design.submissions.order_by('-version_number').first()
    if not submission:
        return
    for key, value in fields.items():
        setattr(submission, key, value)
    submission.save(update_fields=list(fields.keys()))


def transition(design, action, user, request=None, skip_permission=False, **kwargs):
    if action not in WORKFLOW_ACTIONS:
        raise WorkflowError(f'Unknown action: {action}')

    config = WORKFLOW_ACTIONS[action]
    if not skip_permission and not _check_permission(user, config):
        raise WorkflowError('You do not have permission for this action.')

    if design.status not in config['from'] and action != 'cancel':
        raise WorkflowError(
            f'Cannot perform {action} from status {design.status}.'
        )

    old_status = design.status
    new_status = config['to']
    comments = kwargs.get('comments', '')
    hod = get_head_of_design()

    if action == 'assign':
        designer = kwargs.get('designer')
        if not designer or designer.role != UserRole.DESIGNER:
            raise WorkflowError('A valid designer must be selected.')
        if old_status in _CORRECTION_FROM_STATES:
            design.revision_count += 1
        due_date = kwargs.get('due_date')
        instructions = kwargs.get('instructions', '')
        design.assigned_designer = designer
        design.assigned_by = user
        design.due_date = due_date
        design.assignment_instructions = instructions
        design.current_holder = designer
        DesignAssignment.objects.create(
            design=design,
            designer=designer,
            assigned_by=user,
            due_date=due_date,
            instructions=instructions,
        )

    elif action == 'acknowledge':
        _start_deadline(design)
        design.current_holder = hod or user

    elif action == 'request_correction':
        design.current_holder = design.assigned_designer
        DesignReview.objects.create(
            design=design, reviewer=user,
            action='correction', comments=comments,
        )
        _update_latest_submission(design, reviewed_by=user)

    elif action == 'forward_to_designer':
        design.revision_count += 1
        design.current_holder = design.assigned_designer

    elif action in ('send_to_verification', 'accept_design'):
        verifier = kwargs.get('verifier')
        if not verifier:
            raise WorkflowError('A verification team member must be selected.')
        DesignReview.objects.create(
            design=design, reviewer=user,
            action='accept', comments=comments,
        )
        design.assigned_verifier = verifier
        design.current_holder = verifier

    elif action == 'verification_correction':
        design.current_holder = hod or user
        Verification.objects.create(
            design=design, verifier=user,
            action='correction', comments=comments,
        )
        _update_latest_submission(
            design,
            verification_status='Correction Required',
            reviewed_by=user,
        )

    elif action == 'verify_approved':
        Verification.objects.create(
            design=design, verifier=user,
            action='approved', comments=comments,
        )
        design.verified_by = user
        design.current_holder = hod or user
        _update_latest_submission(
            design,
            verification_status='Approved',
            reviewed_by=user,
        )

    elif action == 'send_to_compliance':
        officer = kwargs.get('compliance_officer')
        if not officer:
            raise WorkflowError('A compliance team member must be selected.')
        design.assigned_compliance_officer = officer
        design.current_holder = officer

    elif action == 'compliance_correction':
        design.current_holder = hod or user
        ComplianceReview.objects.create(
            design=design, reviewer=user,
            action='correction', comments=comments,
        )
        _update_latest_submission(
            design,
            approval_status='Correction Required',
            reviewed_by=user,
        )

    elif action == 'compliance_approved':
        ComplianceReview.objects.create(
            design=design, reviewer=user,
            action='approved', comments=comments,
        )
        design.approved_by_compliance = user
        design.current_holder = hod or user
        _update_latest_submission(
            design,
            approval_status='Approved',
            reviewed_by=user,
        )

    elif action == 'submit_work':
        file_name = (kwargs.get('file_name') or '').strip()
        if not file_name:
            raise WorkflowError('File name is required.')
        revision_date = kwargs.get('revision_date') or timezone.localdate()
        file_ref = kwargs.get('internal_file_reference', '')
        notes = kwargs.get('notes', '')
        change_summary = kwargs.get('change_summary', '')
        version = design.submissions.count() + 1
        DesignSubmission.objects.create(
            design=design,
            version_number=version,
            file_name=file_name,
            revision_date=revision_date,
            internal_file_reference=file_ref,
            notes=notes,
            change_summary=change_summary,
            submitted_by=user,
        )
        design.current_holder = hod or user

    elif action == 'accept_assignment':
        _start_stage(design, 'design', user)

    elif action in ('complete', 'hod_fast_complete'):
        design.completion_date = timezone.now()
        design.current_holder = None
        if action == 'hod_fast_complete':
            if old_status in (DesignStatus.UNDER_REVIEW, DesignStatus.SUBMITTED):
                design.verification_skipped_by_hod = True
                design.compliance_skipped_by_hod = True
            elif old_status in (
                DesignStatus.VERIFICATION_PENDING,
                DesignStatus.VERIFICATION_CORRECTION,
                DesignStatus.AWAITING_COMPLIANCE,
            ):
                design.compliance_skipped_by_hod = True

    elif action == 'submit_request':
        design.current_holder = hod

    _end_stage(design, old_status)
    design.status = new_status
    design.save()

    if action == 'submit_work':
        transition(design, 'start_review', hod or user, request=request, skip_permission=True)

    _start_stage(design, new_status, user)
    update_deadline_status(design)

    log_activity(
        'design_request', design.pk, user, action,
        f'Status changed from {old_status} to {new_status}',
        {'old_status': old_status, 'new_status': new_status, 'comments': comments},
    )
    log_activity(
        'project', design.project_id, user, action,
        f'Design {design.design_number}: {old_status} → {new_status}',
    )
    log_audit(
        user, action, 'design_request', design.pk,
        before={'status': old_status},
        after={'status': new_status},
        comment=comments,
        request=request,
    )

    from apps.notifications.services import notify_workflow_transition
    notify_workflow_transition(design, action, user)

    return design


def suggest_designer(design):
    from django.db.models import Count, Q

    active_statuses = [
        DesignStatus.ASSIGNED, DesignStatus.IN_PROGRESS,
        DesignStatus.CORRECTION_REQUIRED, DesignStatus.RESUBMITTED,
    ]
    designers = User.objects.filter(
        role=UserRole.DESIGNER, is_active=True, status='active',
    ).annotate(
        workload=Count(
            'assigned_designs',
            filter=Q(assigned_designs__status__in=active_statuses),
        ),
    ).order_by('workload', 'first_name')
    return designers.first()


def compute_delay_attribution(design):
    durations = design.stage_durations.filter(ended_at__isnull=False)
    stage_totals = {}
    for d in durations:
        days = d.duration_days or 0
        stage_totals[d.stage] = stage_totals.get(d.stage, 0) + days

    if not stage_totals:
        return '', None

    max_stage = max(stage_totals, key=stage_totals.get)
    max_days = stage_totals[max_stage]
    stage_labels = {
        'in_progress': 'Designer',
        'under_review': 'Head of Design',
        'verification_pending': 'Verification Team',
        'compliance_pending': 'Compliance Team',
    }
    source = stage_labels.get(max_stage, max_stage)
    design.delay_source = source
    design.delay_duration_days = max_days
    design.save(update_fields=['delay_source', 'delay_duration_days'])
    return source, max_days
