from django.contrib import admin

from .models import ActivityLog, AuditEntry, StageDuration


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'user', 'created_at')
    list_filter = ('entity_type', 'action')
    search_fields = ('action', 'description')
    readonly_fields = ('created_at',)


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'entity_type', 'entity_id', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type')
    search_fields = ('action', 'comment')
    readonly_fields = ('created_at',)


@admin.register(StageDuration)
class StageDurationAdmin(admin.ModelAdmin):
    list_display = ('design', 'stage', 'started_at', 'ended_at', 'responsible_user')
    list_filter = ('stage',)
