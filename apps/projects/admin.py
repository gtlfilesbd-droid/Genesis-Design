from django.contrib import admin

from .models import Project, ProjectAttachment


class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    readonly_fields = ('name', 'file', 'uploaded_by', 'uploaded_at')
    can_delete = False


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'client_name', 'status', 'health_score', 'created_by', 'start_date')
    list_filter = ('status',)
    search_fields = ('name', 'code', 'client_name')
    inlines = [ProjectAttachmentInline]
