import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

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
