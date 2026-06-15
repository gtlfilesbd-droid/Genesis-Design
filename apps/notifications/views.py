from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    from django.shortcuts import render
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.read_at = timezone.now()
    notification.save(update_fields=['read_at'])
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return redirect('notifications:list')
