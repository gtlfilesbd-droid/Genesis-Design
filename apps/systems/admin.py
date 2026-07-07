from django.contrib import admin

from .models import SystemGroup, SystemName


@admin.register(SystemName)
class SystemNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(SystemGroup)
class SystemGroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'review_user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('group_name', 'review_user__username', 'review_user__first_name')
    filter_horizontal = ('systems',)
    autocomplete_fields = ('review_user',)
