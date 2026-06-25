from datetime import datetime, time, timedelta

from django.utils import timezone


def get_deadline_config():
    from apps.core.models import DeadlineConfiguration

    return DeadlineConfiguration.get_solo()


def duration_days_hours(days, hours):
    return timedelta(days=days, hours=hours)


def add_allowed_duration(start, days, hours, count_weekends=False):
    """Return due datetime from start using allowed days + hours."""
    if count_weekends:
        return _add_business_duration(start, days, hours)
    return start + timedelta(days=days, hours=hours)


def _add_business_duration(start, days, hours):
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current + timedelta(hours=hours)


def warning_threshold_ratio(config=None):
    config = config or get_deadline_config()
    return config.default_warning_percent / 100.0


def target_completion_end_datetime(target_date):
    if not target_date:
        return None
    return timezone.make_aware(datetime.combine(target_date, time(23, 59, 59)))


def is_past_target_completion(design, now=None):
    target_end = target_completion_end_datetime(design.target_completion_date)
    if not target_end or design.completion_date:
        return False
    now = now or timezone.now()
    return now > target_end


def escalation_thresholds(config=None):
    config = config or get_deadline_config()
    return [
        duration_days_hours(config.escalation_level_1_days, config.escalation_level_1_hours),
        duration_days_hours(config.escalation_level_2_days, config.escalation_level_2_hours),
        duration_days_hours(config.escalation_level_3_days, config.escalation_level_3_hours),
        duration_days_hours(config.escalation_level_4_days, config.escalation_level_4_hours),
    ]


def compute_target_escalation_level(breached_at, now=None, config=None):
    if not breached_at:
        return 0
    now = now or timezone.now()
    elapsed = now - breached_at
    level = 0
    for index, delay in enumerate(escalation_thresholds(config), start=1):
        if elapsed >= delay:
            level = index
    return level
