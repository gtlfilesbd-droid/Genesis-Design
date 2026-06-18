import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.designs.models import DesignRequest
from apps.notifications.models import Notification
from apps.workflow.services import WorkflowError, transition


def _json_body(request):
    try:
        return json.loads(request.body.decode()) if request.body else {}
    except json.JSONDecodeError:
        return {}


@login_required
@require_POST
def api_workflow_action(request, pk, action):
    design = get_object_or_404(DesignRequest, pk=pk)
    data = _json_body(request)
    try:
        transition(design, action, request.user, request=request, **data)
        design.refresh_from_db()
        return JsonResponse({
            'success': True,
            'status': design.status,
            'status_display': design.get_status_display(),
        })
    except WorkflowError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def api_mark_notification_read(request):
    data = _json_body(request)
    notif_id = data.get('id') or request.POST.get('id')
    notification = get_object_or_404(Notification, pk=notif_id, user=request.user)
    from django.utils import timezone
    notification.read_at = timezone.now()
    notification.save(update_fields=['read_at'])
    return JsonResponse({'success': True})


@login_required
@require_GET
def api_notification_unread_count(request):
    count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
    return JsonResponse({'count': count})


@login_required
@require_GET
def api_notification_badge(request):
    count = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
    return render(request, 'components/notification_badge.html', {
        'unread_notification_count': count,
    })


@login_required
@require_GET
def api_notification_recent(request):
    recent = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
    return JsonResponse({
        'unread_count': unread,
        'notifications': [
            {
                'id': n.pk,
                'title': n.title,
                'message': n.message,
                'link': n.link,
                'read': n.read_at is not None,
                'created_at': n.created_at.isoformat(),
            }
            for n in recent
        ],
    })
