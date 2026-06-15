from django.contrib import admin

from .models import Notification, NotificationSetting


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'read_at', 'created_at')
    list_filter = ('notification_type', 'read_at')


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = (
        'enable_email', 'enable_in_app', 'enable_whatsapp',
        'enable_sms', 'sla_warning_hours',
    )

    def has_add_permission(self, request):
        return not NotificationSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
