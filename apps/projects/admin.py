from django.contrib import admin

from .models import Project, ProjectAttachment, ProjectDirector, ProjectEngineer


class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    readonly_fields = ('name', 'file', 'uploaded_by', 'uploaded_at')
    can_delete = False


@admin.register(ProjectDirector)
class ProjectDirectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(ProjectEngineer)
class ProjectEngineerAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'client_name', 'project_director', 'project_engineer',
        'project_coordinator', 'project_manager', 'status', 'health_score',
        'created_by', 'start_date',
    )
    list_filter = ('status',)
    search_fields = ('name', 'code', 'client_name')
    autocomplete_fields = (
        'project_director', 'project_engineer',
        'project_coordinator', 'project_manager',
    )
    inlines = [ProjectAttachmentInline]
