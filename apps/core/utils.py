from apps.core.models import ActivityLog


def log_activity(entity_type, entity_id, user, action, description='', metadata=None):
    ActivityLog.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        action=action,
        description=description,
        metadata=metadata or {},
    )
