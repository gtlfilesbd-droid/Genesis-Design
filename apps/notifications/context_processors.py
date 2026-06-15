def unread_notifications(request):
    if request.user.is_authenticated:
        from .models import Notification
        count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
        recent = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
        return {'unread_notification_count': count, 'recent_notifications': recent}
    return {'unread_notification_count': 0, 'recent_notifications': []}
