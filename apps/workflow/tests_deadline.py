from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.core.models import DeadlineConfiguration
from apps.designs.models import DrawingType
from apps.workflow.deadline_utils import (
    add_allowed_duration,
    compute_target_escalation_level,
    warning_threshold_ratio,
)


class DeadlineUtilsTests(TestCase):
    def test_warning_threshold_uses_configuration(self):
        config = DeadlineConfiguration.get_solo()
        config.default_warning_percent = 20
        self.assertEqual(warning_threshold_ratio(config), 0.2)

    def test_add_allowed_duration_with_hours(self):
        start = timezone.now()
        due = add_allowed_duration(start, days=2, hours=6, count_weekends=False)
        self.assertEqual(due, start + timedelta(days=2, hours=6))

    def test_escalation_levels_follow_configured_delays(self):
        config = DeadlineConfiguration.get_solo()
        config.escalation_level_1_days = 1
        config.escalation_level_1_hours = 0
        config.escalation_level_2_days = 2
        config.escalation_level_2_hours = 0
        config.escalation_level_3_days = 3
        config.escalation_level_3_hours = 0
        config.escalation_level_4_days = 4
        config.escalation_level_4_hours = 0
        config.save()

        breached_at = timezone.now() - timedelta(days=2, hours=12)
        self.assertEqual(compute_target_escalation_level(breached_at, config=config), 2)

    def test_drawing_type_duration_label(self):
        drawing_type = DrawingType.objects.create(
            name='Shop Drawing', code_prefix='SD', allowed_days=3, allowed_hours=4,
        )
        self.assertEqual(drawing_type.allowed_duration_label, '3 days, 4 hours')
