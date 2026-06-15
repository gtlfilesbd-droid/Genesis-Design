from django.contrib import admin

from .models import (
    DesignAssignment, DesignRequest, DesignReview, DesignSubmission,
    DrawingType, SLARecord, Verification,
)


@admin.register(DrawingType)
class DrawingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_prefix', 'default_sla_days', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code_prefix')


class DesignSubmissionInline(admin.TabularInline):
    model = DesignSubmission
    extra = 0
    readonly_fields = ('version_number', 'submitted_at')


@admin.register(DesignRequest)
class DesignRequestAdmin(admin.ModelAdmin):
    list_display = (
        'design_number', 'project', 'drawing_type', 'status',
        'priority', 'assigned_designer', 'sla_status',
    )
    list_filter = ('status', 'priority', 'sla_status', 'drawing_type')
    search_fields = ('design_number', 'project__name', 'project__code')
    readonly_fields = ('design_number', 'created_at', 'updated_at')
    inlines = [DesignSubmissionInline]


@admin.register(SLARecord)
class SLARecordAdmin(admin.ModelAdmin):
    list_display = ('design', 'status', 'started_at', 'due_at', 'escalation_level')
    list_filter = ('status', 'escalation_level')
