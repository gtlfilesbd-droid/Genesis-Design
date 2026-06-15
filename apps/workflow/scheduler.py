"""In-process deadline scheduler for development (no Celery/Redis required)."""

import logging
import threading
import time

logger = logging.getLogger(__name__)

STATUS_CHECK_INTERVAL = 30 * 60
ESCALATION_CHECK_INTERVAL = 60 * 60
TICK_INTERVAL = 60

_scheduler_thread = None
_stop_event = threading.Event()


def _run_scheduler_loop():
    from apps.workflow.tasks import check_deadline_statuses, process_deadline_escalations

    last_status_check = 0.0
    last_escalation_check = 0.0

    logger.info(
        'Deadline scheduler active — status every %s min, escalation every %s min',
        STATUS_CHECK_INTERVAL // 60,
        ESCALATION_CHECK_INTERVAL // 60,
    )

    try:
        check_deadline_statuses()
        process_deadline_escalations()
    except Exception:
        logger.exception('Initial deadline scheduler run failed')
    last_status_check = time.monotonic()
    last_escalation_check = time.monotonic()

    while not _stop_event.is_set():
        now = time.monotonic()
        try:
            if now - last_status_check >= STATUS_CHECK_INTERVAL:
                count = check_deadline_statuses()
                last_status_check = now
                logger.debug('Deadline status check completed (%s designs)', count)

            if now - last_escalation_check >= ESCALATION_CHECK_INTERVAL:
                count = process_deadline_escalations()
                last_escalation_check = now
                logger.debug('Deadline escalation check completed (%s records)', count)
        except Exception:
            logger.exception('Deadline scheduler tick failed')

        _stop_event.wait(TICK_INTERVAL)


def start_background_scheduler():
    global _scheduler_thread

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler_loop,
        name='genesis-deadline-scheduler',
        daemon=True,
    )
    _scheduler_thread.start()


def stop_background_scheduler():
    _stop_event.set()
