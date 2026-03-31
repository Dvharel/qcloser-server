from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task(name="core.tasks.flush_expired_tokens")
def flush_expired_tokens():
    logger.info("Running flushexpiredtokens...")
    call_command("flushexpiredtokens")
    logger.info("flushexpiredtokens complete.")
