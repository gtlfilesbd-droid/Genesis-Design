from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Team, User


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'created_at')
    search_fields = ('name', 'department')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'employee_id', 'get_full_name', 'role',
        'department', 'status', 'is_active',
    )
    list_filter = ('role', 'status', 'department', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'employee_id', 'email')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Genesis Profile', {
            'fields': (
                'employee_id', 'designation', 'department', 'role',
                'team', 'manager', 'mobile_number', 'joining_date', 'status',
                'avatar',
            ),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Genesis Profile', {
            'fields': (
                'employee_id', 'designation', 'department', 'role',
                'team', 'manager', 'mobile_number', 'joining_date', 'status',
                'avatar',
            ),
        }),
    )
