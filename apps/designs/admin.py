from django.contrib import admin

from .models import (
    DesignAssignment, DesignRequest, DesignReview, DesignSubmission,
    DrawingType, DeadlineRecord, Verification,
)


@admin.register(DrawingType)
class DrawingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_prefix', 'allowed_days', 'allowed_hours', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code_prefix')


class DesignSubmissionInline(admin.TabularInline):
    model = DesignSubmission
    extra = 0
    readonly_fields = (
        'version_number', 'file_name', 'revision_date', 'submitted_at',
        'file', 'internal_file_reference', 'change_summary', 'notes',
        'verification_status', 'approval_status', 'reviewed_by',
    )
    fields = readonly_fields


@admin.register(DesignRequest)
class DesignRequestAdmin(admin.ModelAdmin):
    list_display = (
        'design_number', 'project', 'drawing_type', 'status',
        'priority', 'assigned_designer', 'deadline_status',
    )
    list_filter = ('status', 'priority', 'deadline_status', 'drawing_type')
    search_fields = ('design_number', 'project__name', 'project__code')
    readonly_fields = ('design_number', 'created_at', 'updated_at')
    inlines = [DesignSubmissionInline]


@admin.register(DeadlineRecord)
class DeadlineRecordAdmin(admin.ModelAdmin):
    list_display = ('design', 'status', 'started_at', 'due_at', 'escalation_level')
    list_filter = ('status', 'escalation_level')
