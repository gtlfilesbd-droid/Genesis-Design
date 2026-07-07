from django.conf import settings
from django.db import models
from django.db.models import Max


class DrawingType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code_prefix = models.CharField(max_length=10)
    allowed_days = models.PositiveSmallIntegerField(default=5)
    allowed_hours = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def allowed_duration_label(self):
        parts = []
        if self.allowed_days:
            parts.append(f'{self.allowed_days} day{"s" if self.allowed_days != 1 else ""}')
        if self.allowed_hours:
            parts.append(f'{self.allowed_hours} hour{"s" if self.allowed_hours != 1 else ""}')
        return ', '.join(parts) if parts else '0 hours'


class DesignPriority(models.TextChoices):
    CRITICAL = 'critical', 'Critical'
    HIGH = 'high', 'High'
    MEDIUM = 'medium', 'Medium'
    LOW = 'low', 'Low'


class DesignStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft Request'
    REQUEST_UNDER_REVIEW = 'request_under_review', 'Request Under Review'
    ENGINEER_PENDING_ACK = 'engineer_pending_acknowledgement', 'Engineer Pending Acknowledgement'
    ENGINEER_IN_PROGRESS = 'engineer_in_progress', 'Engineer In Progress'
    NEW_REQUEST = 'new_request', 'New Request'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    ASSIGNED = 'assigned', 'Assigned'
    IN_PROGRESS = 'in_progress', 'In Progress'
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    CORRECTION_REQUIRED = 'correction_required', 'Correction Required'
    RESUBMITTED = 'resubmitted', 'Re-Submitted'
    VERIFICATION_PENDING_ACK = 'verification_pending_acknowledgement', 'Verification Pending Acknowledgement'
    VERIFICATION_PENDING = 'verification_pending', 'Verification Pending'
    VERIFICATION_CORRECTION = 'verification_correction', 'Verification Correction'
    AWAITING_COMPLIANCE = 'awaiting_compliance', 'Awaiting Compliance'
    COMPLIANCE_PENDING_ACK = 'compliance_pending_acknowledgement', 'Compliance Pending Acknowledgement'
    COMPLIANCE_PENDING = 'compliance_pending', 'Compliance Pending'
    COMPLIANCE_CORRECTION = 'compliance_correction', 'Compliance Correction'
    FINAL_APPROVAL_PENDING = 'final_approval_pending', 'Final Approval Pending'
    APPROVED = 'approved', 'Approved'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class DeadlineStatus(models.TextChoices):
    GREEN = 'green', 'On Track'
    YELLOW = 'yellow', 'Deadline Warning'
    RED = 'red', 'Deadline Missed'


class PrimaryStatus(models.TextChoices):
    NEW = 'new', 'New'
    RUNNING = 'running', 'Running'
    VERIFICATION = 'verification', 'Verification'
    APPROVED = 'approved', 'Approved'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


PRIMARY_STATUS_MAP = {
    DesignStatus.DRAFT: PrimaryStatus.NEW,
    DesignStatus.REQUEST_UNDER_REVIEW: PrimaryStatus.NEW,
    DesignStatus.ENGINEER_PENDING_ACK: PrimaryStatus.NEW,
    DesignStatus.ENGINEER_IN_PROGRESS: PrimaryStatus.NEW,
    DesignStatus.NEW_REQUEST: PrimaryStatus.NEW,
    DesignStatus.ACKNOWLEDGED: PrimaryStatus.RUNNING,
    DesignStatus.ASSIGNED: PrimaryStatus.RUNNING,
    DesignStatus.IN_PROGRESS: PrimaryStatus.RUNNING,
    DesignStatus.SUBMITTED: PrimaryStatus.RUNNING,
    DesignStatus.UNDER_REVIEW: PrimaryStatus.RUNNING,
    DesignStatus.CORRECTION_REQUIRED: PrimaryStatus.RUNNING,
    DesignStatus.RESUBMITTED: PrimaryStatus.RUNNING,
    DesignStatus.VERIFICATION_PENDING_ACK: PrimaryStatus.VERIFICATION,
    DesignStatus.VERIFICATION_PENDING: PrimaryStatus.VERIFICATION,
    DesignStatus.VERIFICATION_CORRECTION: PrimaryStatus.VERIFICATION,
    DesignStatus.AWAITING_COMPLIANCE: PrimaryStatus.VERIFICATION,
    DesignStatus.COMPLIANCE_PENDING_ACK: PrimaryStatus.VERIFICATION,
    DesignStatus.COMPLIANCE_PENDING: PrimaryStatus.VERIFICATION,
    DesignStatus.COMPLIANCE_CORRECTION: PrimaryStatus.VERIFICATION,
    DesignStatus.FINAL_APPROVAL_PENDING: PrimaryStatus.VERIFICATION,
    DesignStatus.APPROVED: PrimaryStatus.APPROVED,
    DesignStatus.COMPLETED: PrimaryStatus.COMPLETED,
    DesignStatus.CANCELLED: PrimaryStatus.CANCELLED,
}


class DesignRequest(models.Model):
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='design_requests',
    )
    drawing_type = models.ForeignKey(
        DrawingType,
        on_delete=models.PROTECT,
        related_name='design_requests',
    )
    design_number = models.CharField(max_length=50, unique=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=DesignPriority.choices,
        default=DesignPriority.MEDIUM,
    )
    target_completion_date = models.DateField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    request_message = models.TextField(blank=True)
    status = models.CharField(
        max_length=40,
        choices=DesignStatus.choices,
        default=DesignStatus.DRAFT,
    )
    primary_status = models.CharField(
        max_length=20,
        choices=PrimaryStatus.choices,
        default=PrimaryStatus.NEW,
    )
    deadline_missed = models.BooleanField(default=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_designs',
    )
    assigned_designer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_designs',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='designs_assigned',
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_designs',
    )
    assigned_verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verifier_assignments',
    )
    assigned_compliance_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_assignments',
    )
    systems = models.ManyToManyField(
        'systems.SystemName',
        related_name='design_requests',
        blank=True,
    )
    assigned_review_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_assigned_designs',
    )
    review_acknowledged_at = models.DateTimeField(null=True, blank=True)
    review_cancel_reason = models.TextField(blank=True)
    review_cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)
    main_design_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_design_lead_assignments',
    )
    sub_design_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_design_lead_assignments',
    )
    assigned_site_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_engineer_assignments',
    )
    engineer_due_date = models.DateTimeField(null=True, blank=True)
    engineer_instructions = models.TextField(blank=True)
    engineer_assigned_at = models.DateTimeField(null=True, blank=True)
    engineer_acknowledged_at = models.DateTimeField(null=True, blank=True)
    engineer_submitted_at = models.DateTimeField(null=True, blank=True)
    engineer_site_notes = models.TextField(blank=True)
    approved_by_compliance = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_approvals',
    )
    verification_skipped_by_hod = models.BooleanField(default=False)
    compliance_skipped_by_hod = models.BooleanField(default=False)
    current_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='held_designs',
    )
    assignment_instructions = models.TextField(blank=True)
    verification_due_date = models.DateTimeField(null=True, blank=True)
    verification_instructions = models.TextField(blank=True)
    verification_assigned_at = models.DateTimeField(null=True, blank=True)
    verification_acknowledged_at = models.DateTimeField(null=True, blank=True)
    compliance_due_date = models.DateTimeField(null=True, blank=True)
    compliance_instructions = models.TextField(blank=True)
    compliance_assigned_at = models.DateTimeField(null=True, blank=True)
    compliance_acknowledged_at = models.DateTimeField(null=True, blank=True)
    revision_count = models.PositiveSmallIntegerField(default=0)
    completion_date = models.DateTimeField(null=True, blank=True)
    deadline_start = models.DateTimeField(null=True, blank=True)
    deadline_due = models.DateTimeField(null=True, blank=True)
    deadline_status = models.CharField(
        max_length=10,
        choices=DeadlineStatus.choices,
        default=DeadlineStatus.GREEN,
    )
    delay_source = models.CharField(max_length=100, blank=True)
    delay_duration_days = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    reference_design = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referenced_by',
    )
    sequence_number = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    action_sla_breached_at = models.DateTimeField(null=True, blank=True)
    action_sla_breach_status = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.design_number or f'Design #{self.pk}'

    def save(self, *args, **kwargs):
        if not self.design_number and self.project_id and self.drawing_type_id:
            self.design_number = self._generate_design_number()
        self.primary_status = PRIMARY_STATUS_MAP.get(self.status, PrimaryStatus.NEW)
        self.deadline_missed = self.deadline_status == DeadlineStatus.RED
        super().save(*args, **kwargs)

    def _generate_design_number(self):
        last_seq = (
            DesignRequest.objects.filter(
                project=self.project,
                drawing_type=self.drawing_type,
            )
            .aggregate(max_seq=Max('sequence_number'))
        )['max_seq'] or 0
        self.sequence_number = last_seq + 1
        return f'{self.project.code}-{self.drawing_type.code_prefix}-{self.sequence_number:03d}'

    @property
    def action_due_at(self):
        from apps.workflow.action_sla import get_action_due_at
        return get_action_due_at(self)

    @property
    def is_action_overdue(self):
        from apps.workflow.action_sla import is_action_overdue
        return is_action_overdue(self)

    @property
    def is_overdue(self):
        from django.utils import timezone
        if not self.due_date:
            return False
        if self.status in [DesignStatus.COMPLETED, DesignStatus.CANCELLED]:
            return False
        return timezone.now() > self.due_date

    @property
    def is_engineer_work_overdue(self):
        from django.utils import timezone
        if not self.engineer_due_date:
            return False
        if self.status not in (
            DesignStatus.ENGINEER_PENDING_ACK,
            DesignStatus.ENGINEER_IN_PROGRESS,
        ):
            return False
        return timezone.now() > self.engineer_due_date

    @property
    def system_names_display(self):
        names = list(self.systems.values_list('name', flat=True))
        return ', '.join(names) if names else ''

    @property
    def cancel_reason_display(self):
        return self.cancel_reason or self.review_cancel_reason

    @property
    def cancelled_at(self):
        if self.status != DesignStatus.CANCELLED:
            return None
        from apps.designs.lifecycle_timeline import _resolve_cancelled_at
        return _resolve_cancelled_at(self)

    @property
    def cancelled_by_display(self):
        if self.status != DesignStatus.CANCELLED:
            return ''
        from apps.designs.lifecycle_timeline import _resolve_cancelled_by
        info = _resolve_cancelled_by(self)
        return info['display_name'] if info else ''

    def is_site_lead_user(self, user):
        if not user or not user.is_authenticated:
            return False
        user_pk = user.pk
        if self.main_design_lead_id or self.sub_design_lead_id:
            return user_pk in (self.main_design_lead_id, self.sub_design_lead_id)
        return self.assigned_site_engineer_id == user_pk

    def site_lead_users(self):
        if self.main_design_lead_id or self.sub_design_lead_id:
            users = []
            if self.main_design_lead_id:
                users.append(self.main_design_lead)
            if self.sub_design_lead_id:
                users.append(self.sub_design_lead)
            return users
        if self.assigned_site_engineer_id:
            return [self.assigned_site_engineer]
        return []

    @property
    def verification_status(self):
        if self.status in [DesignStatus.APPROVED, DesignStatus.COMPLETED]:
            return 'Approved'
        if self.status == DesignStatus.VERIFICATION_CORRECTION:
            return 'Correction'
        if self.status in [
            DesignStatus.VERIFICATION_PENDING,
            DesignStatus.VERIFICATION_CORRECTION,
            DesignStatus.AWAITING_COMPLIANCE,
            DesignStatus.FINAL_APPROVAL_PENDING,
        ]:
            return 'Pending'
        if self.status in [DesignStatus.COMPLIANCE_PENDING, DesignStatus.COMPLIANCE_CORRECTION]:
            return 'Compliance Pending'
        return 'N/A'

    @property
    def approval_status(self):
        if self.status == DesignStatus.COMPLETED:
            return 'Completed'
        if self.status == DesignStatus.APPROVED:
            return 'Approved'
        if self.status == DesignStatus.CANCELLED:
            return 'Cancelled'
        return 'Pending'

    @property
    def requested_at(self):
        return self.created_at

    @property
    def acknowledged_at(self):
        return self.deadline_start

    @property
    def assigned_at(self):
        assignment = self.assignments.order_by('assigned_at').first()
        return assignment.assigned_at if assignment else None

    @property
    def target_date(self):
        return self.target_completion_date

    @property
    def completed_at(self):
        return self.completion_date

    @property
    def correction_count(self):
        return self.revision_count


class DesignAssignment(models.Model):
    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    designer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='design_assignments',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assignments_made',
    )
    due_date = models.DateTimeField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']


class DesignSubmission(models.Model):
    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    version_number = models.PositiveSmallIntegerField()
    file_name = models.CharField(max_length=255, blank=True)
    revision_date = models.DateField(null=True, blank=True)
    file = models.FileField(
        upload_to='design_submissions/%Y/%m/',
        blank=True,
        null=True,
        help_text='Deprecated — reference-only storage; do not upload new files.',
    )
    internal_file_reference = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    change_summary = models.TextField(blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='design_submissions',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions',
    )
    verification_status = models.CharField(max_length=50, blank=True)
    approval_status = models.CharField(max_length=50, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = [('design', 'version_number')]

    def __str__(self):
        return f'{self.design.design_number} V{self.version_number}'


class DesignReview(models.Model):
    class ReviewAction(models.TextChoices):
        ACCEPT = 'accept', 'Accept'
        CORRECTION = 'correction', 'Correction Required'

    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='design_reviews',
    )
    action = models.CharField(max_length=20, choices=ReviewAction.choices)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Verification(models.Model):
    class VerificationAction(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        CORRECTION = 'correction', 'Correction Required'

    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='verifications',
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='verifications_done',
    )
    action = models.CharField(max_length=20, choices=VerificationAction.choices)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ComplianceReview(models.Model):
    class ComplianceAction(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        CORRECTION = 'correction', 'Correction Required'

    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='compliance_reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='compliance_reviews_done',
    )
    action = models.CharField(max_length=20, choices=ComplianceAction.choices)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class DeadlineRecord(models.Model):
    design = models.OneToOneField(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='deadline_record',
    )
    started_at = models.DateTimeField()
    due_at = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=DeadlineStatus.choices,
        default=DeadlineStatus.GREEN,
    )
    breached_at = models.DateTimeField(null=True, blank=True)
    breach_notified_at = models.DateTimeField(null=True, blank=True)
    warning_notified_at = models.DateTimeField(null=True, blank=True)
    escalation_level = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class DesignComment(models.Model):
    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='design_comments',
    )
    message = models.TextField()
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='mentioned_in_comments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def content(self):
        return self.message

    def __str__(self):
        return f'{self.author}: {self.message[:50]}'


class RequestAttachment(models.Model):
    design = models.ForeignKey(
        DesignRequest,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(upload_to='request_attachments/%Y/%m/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_request_attachments',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.filename or str(self.pk)
