import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sweep-stuck-deliveries-every-5-minutes": {
        "task": "services.conversations.tasks.sweep_stuck_deliveries",
        "schedule": 300,
    },
}
