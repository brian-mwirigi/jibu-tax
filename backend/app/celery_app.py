"""Celery application. Redis is the broker so ledger writes never block the voice webhook."""

from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jibutax",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.ledger_tasks", "app.workers.filing_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=True,
)


@worker_process_init.connect
def _init_database(**_kwargs) -> None:
    from app.database import init_db

    init_db()
