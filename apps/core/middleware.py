from apps.core.models import AuditEntry


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._audit_ip = self._get_client_ip(request)
        request._audit_device = request.META.get('HTTP_USER_AGENT', '')[:255]
        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


def log_audit(user, action, entity_type='', entity_id=None, before=None, after=None,
              comment='', request=None):
    AuditEntry.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=getattr(request, '_audit_ip', None) if request else None,
        device=getattr(request, '_audit_device', '') if request else '',
        before_value=before,
        after_value=after,
        comment=comment,
    )
