import os
from celery import Celery
from celery.schedules import crontab
import core.tasks  # noqa: F401 — ensures flush_expired_tokens is registered

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sweep-stuck-deliveries-every-5-minutes": {
        "task": "services.conversations.tasks.sweep_stuck_deliveries",
        "schedule": 300,
    },
    "flush-expired-tokens": {
        "task": "core.tasks.flush_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
}
