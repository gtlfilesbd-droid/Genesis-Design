from django.contrib import admin

from .models import Permission, ProjectMembership, RoleTemplate, UserPermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category')
    list_filter = ('category',)
    search_fields = ('code', 'name')


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission', 'is_active', 'granted_at')
    list_filter = ('is_active', 'permission__category')
    search_fields = ('user__username', 'permission__code')


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'is_active', 'added_at')
    list_filter = ('is_active',)
    filter_horizontal = ('permissions',)
    search_fields = ('user__username', 'project__code')


@admin.register(RoleTemplate)
class RoleTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_system_template', 'created_at')
    filter_horizontal = ('permissions',)
    search_fields = ('name',)
