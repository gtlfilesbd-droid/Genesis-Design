from django.core.exceptions import ValidationError

from .models import SystemGroup


def resolve_group_for_systems(systems):
    """Return the single active SystemGroup covering all selected systems."""
    system_list = list(systems)
    if not system_list:
        raise ValidationError('At least one system must be selected.')

    groups = (
        SystemGroup.objects.filter(is_active=True, systems__in=system_list)
        .distinct()
        .prefetch_related('systems')
    )
    group_list = list(groups)
    if not group_list:
        raise ValidationError(
            'Selected system(s) are not assigned to any active system group.'
        )
    if len(group_list) > 1:
        raise ValidationError(
            'All selected systems must belong to the same system group.'
        )

    group = group_list[0]
    group_system_ids = set(group.systems.filter(is_active=True).values_list('pk', flat=True))
    selected_ids = {s.pk for s in system_list}
    if not selected_ids.issubset(group_system_ids):
        missing = [s.name for s in system_list if s.pk not in group_system_ids]
        raise ValidationError(
            f'Selected system(s) are not in group "{group.group_name}": {", ".join(missing)}'
        )
    inactive = [s.name for s in system_list if not s.is_active]
    if inactive:
        raise ValidationError(f'Inactive system(s) cannot be selected: {", ".join(inactive)}')

    return group
