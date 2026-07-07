from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SystemName(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'System Name'
        verbose_name_plural = 'System Names'

    def __str__(self):
        return self.name


class SystemGroup(models.Model):
    group_name = models.CharField(max_length=150, unique=True)
    systems = models.ManyToManyField(
        SystemName,
        related_name='system_groups',
        blank=True,
    )
    review_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='system_review_groups',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group_name']
        verbose_name = 'System Name Group'
        verbose_name_plural = 'System Name Groups'

    def __str__(self):
        return self.group_name

    def clean(self):
        super().clean()
        if not self.pk:
            return
        system_ids = list(self.systems.values_list('pk', flat=True))
        if not system_ids:
            return
        conflicts = (
            SystemGroup.objects.filter(is_active=True, systems__in=system_ids)
            .exclude(pk=self.pk)
            .prefetch_related('systems')
        )
        for other in conflicts:
            overlap = set(other.systems.values_list('pk', flat=True)) & set(system_ids)
            if overlap:
                names = SystemName.objects.filter(pk__in=overlap).values_list('name', flat=True)
                raise ValidationError(
                    f'System(s) already assigned to another active group: {", ".join(names)}'
                )
