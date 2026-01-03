"""Celery application configuration with dead letter queue support."""

import json
import os
from datetime import datetime
from typing import Any

from celery import Celery
from celery.signals import task_failure, task_success, task_retry, worker_shutdown, worker_shutting_down
from kombu import Exchange, Queue
import structlog

from app.config import settings

logger = structlog.get_logger()

# Define exchanges
default_exchange = Exchange("keylia", type="direct")
dlx_exchange = Exchange("keylia.dlx", type="direct")

# Define queues with dead letter routing
# When a task fails after max retries, it's routed to the dead letter queue
task_queues = (
    # Main task queues with dead letter routing
    Queue(
        "celery",
        default_exchange,
        routing_key="celery",
        queue_arguments={
            "x-dead-letter-exchange": "keylia.dlx",
            "x-dead-letter-routing-key": "dead_letter",
        },
    ),
    Queue(
        "video",
        default_exchange,
        routing_key="video",
        queue_arguments={
            "x-dead-letter-exchange": "keylia.dlx",
            "x-dead-letter-routing-key": "dead_letter",
        },
    ),
    Queue(
        "graphics",
        default_exchange,
        routing_key="graphics",
        queue_arguments={
            "x-dead-letter-exchange": "keylia.dlx",
            "x-dead-letter-routing-key": "dead_letter",
        },
    ),
    Queue(
        "ai",
        default_exchange,
        routing_key="ai",
        queue_arguments={
            "x-dead-letter-exchange": "keylia.dlx",
            "x-dead-letter-routing-key": "dead_letter",
        },
    ),
    # Dead letter queue - collects failed tasks for investigation
    Queue(
        "dead_letter",
        dlx_exchange,
        routing_key="dead_letter",
    ),
)

celery_app = Celery(
    "keylia_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.render_video",
        "app.workers.tasks.render_infographic",
        "app.workers.tasks.generate_voiceover",
        "app.workers.tasks.fal_video",
        "app.workers.tasks.tour_video",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit 55 minutes

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=2,

    # Queue configuration
    task_queues=task_queues,
    task_default_queue="celery",
    task_default_exchange="keylia",
    task_default_routing_key="celery",

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours

    # Error handling
    task_acks_late=True,  # Ack after task completes (not when received)
    task_reject_on_worker_lost=True,  # Reject if worker dies mid-task

    # Retry settings (can be overridden per-task)
    task_default_retry_delay=60,  # 1 minute between retries
    task_max_retries=3,
)

# Task routing
celery_app.conf.task_routes = {
    "render_video": {"queue": "video"},
    "generate_scene_clip": {"queue": "video"},
    "generate_preview": {"queue": "video"},
    "fal_generate_video": {"queue": "video"},
    "fal_generate_property_tour": {"queue": "video"},
    "fal_submit_async": {"queue": "video"},
    "fal_check_status": {"queue": "video"},
    "fal_get_result": {"queue": "video"},
    "render_infographic": {"queue": "graphics"},
    "generate_voiceover": {"queue": "ai"},
    "generate_tour_video": {"queue": "video"},
    "regenerate_scene": {"queue": "video"},
}


# ============================================================================
# Task lifecycle signals for monitoring and dead letter handling
# ============================================================================

@task_failure.connect
def handle_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **signal_kwargs
):
    """
    Handle task failure - log and potentially notify.

    This fires when a task fails completely (after all retries exhausted).
    The task will be routed to the dead letter queue by RabbitMQ/Redis.
    """
    # Build failure record
    failure_record = {
        "task_id": task_id,
        "task_name": sender.name if sender else "unknown",
        "exception_type": type(exception).__name__ if exception else "unknown",
        "exception_message": str(exception)[:500] if exception else None,
        "args": _safe_serialize(args),
        "kwargs": _safe_serialize(kwargs),
        "failed_at": datetime.utcnow().isoformat(),
    }

    logger.error(
        "Task failed permanently (routed to DLQ)",
        **failure_record,
    )

    # Store failure in Redis for admin visibility
    try:
        import redis
        r = redis.from_url(settings.CELERY_RESULT_BACKEND)

        # Store in a sorted set by timestamp
        key = "keylia:dlq:failures"
        r.zadd(key, {json.dumps(failure_record): datetime.utcnow().timestamp()})

        # Keep only last 1000 failures
        r.zremrangebyrank(key, 0, -1001)

        # Also store in a hash by task_id for lookup
        r.hset("keylia:dlq:by_id", task_id, json.dumps(failure_record))
    except Exception as e:
        logger.warning("Failed to store DLQ record in Redis", error=str(e))


@task_retry.connect
def handle_task_retry(
    sender=None,
    request=None,
    reason=None,
    einfo=None,
    **signal_kwargs
):
    """Log task retries for monitoring."""
    logger.warning(
        "Task being retried",
        task_id=request.id if request else None,
        task_name=sender.name if sender else "unknown",
        retry_reason=str(reason)[:200] if reason else None,
    )


@task_success.connect
def handle_task_success(
    sender=None,
    result=None,
    **signal_kwargs
):
    """Log successful task completion for monitoring."""
    logger.info(
        "Task completed successfully",
        task_name=sender.name if sender else "unknown",
    )


def _safe_serialize(obj: Any, max_length: int = 500) -> str:
    """Safely serialize an object to string for logging."""
    try:
        serialized = json.dumps(obj, default=str)
        if len(serialized) > max_length:
            return serialized[:max_length] + "..."
        return serialized
    except Exception:
        return "<unserializable>"


# ============================================================================
# Dead letter queue management utilities
# ============================================================================

def get_dlq_failures(limit: int = 100) -> list[dict]:
    """Get recent failures from the dead letter queue."""
    try:
        import redis
        r = redis.from_url(settings.CELERY_RESULT_BACKEND)

        # Get most recent failures
        key = "keylia:dlq:failures"
        items = r.zrevrange(key, 0, limit - 1)

        return [json.loads(item) for item in items]
    except Exception as e:
        logger.error("Failed to retrieve DLQ failures", error=str(e))
        return []


def get_dlq_failure_by_id(task_id: str) -> dict | None:
    """Get a specific failure by task ID."""
    try:
        import redis
        r = redis.from_url(settings.CELERY_RESULT_BACKEND)

        data = r.hget("keylia:dlq:by_id", task_id)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error("Failed to retrieve DLQ failure", task_id=task_id, error=str(e))
        return None


def retry_failed_task(task_id: str) -> bool:
    """
    Manually retry a failed task from the dead letter queue.

    Returns True if the task was successfully re-queued.
    """
    failure = get_dlq_failure_by_id(task_id)
    if not failure:
        logger.warning("Failed task not found in DLQ", task_id=task_id)
        return False

    try:
        # Get the original task
        task_name = failure.get("task_name")
        args = json.loads(failure.get("args", "[]"))
        kwargs = json.loads(failure.get("kwargs", "{}"))

        # Re-queue the task
        celery_app.send_task(task_name, args=args, kwargs=kwargs)

        logger.info("DLQ task re-queued", task_id=task_id, task_name=task_name)
        return True
    except Exception as e:
        logger.error("Failed to retry DLQ task", task_id=task_id, error=str(e))
        return False


def clear_dlq() -> int:
    """Clear all failures from the dead letter queue. Returns count of cleared items."""
    try:
        import redis
        r = redis.from_url(settings.CELERY_RESULT_BACKEND)

        count = r.zcard("keylia:dlq:failures")
        r.delete("keylia:dlq:failures")
        r.delete("keylia:dlq:by_id")

        logger.info("DLQ cleared", count=count)
        return count
    except Exception as e:
        logger.error("Failed to clear DLQ", error=str(e))
        return 0


# ============================================================================
# Graceful shutdown handlers
# ============================================================================

@worker_shutting_down.connect
def handle_worker_shutting_down(sig, how, exitcode, **kwargs):
    """
    Handle worker shutdown signal - beginning of shutdown process.

    This fires when the worker receives a shutdown signal (SIGTERM, SIGINT).
    At this point, new tasks won't be accepted, but current tasks continue.
    """
    logger.warning(
        "Worker shutdown initiated",
        signal=sig,
        how=how,
        exitcode=exitcode,
    )


@worker_shutdown.connect
def handle_worker_shutdown(**kwargs):
    """
    Handle worker shutdown - cleanup after shutdown completes.

    This fires after the worker has finished processing current tasks.
    With task_acks_late=True, any in-progress tasks when shutdown started
    will be requeued and picked up by another worker.

    Cleanup tasks:
    - Clean up any temporary files
    - Close any remaining connections
    - Log final status
    """
    import tempfile
    import shutil
    import glob

    logger.info("Worker shutting down - performing cleanup")

    # Clean up any orphaned temp directories from video generation
    try:
        temp_base = tempfile.gettempdir()
        # Pattern for our temp directories
        patterns = [
            f"{temp_base}/tmp*",  # Default tempfile pattern
        ]

        orphaned_count = 0
        for pattern in patterns:
            for temp_path in glob.glob(pattern):
                # Only clean if it looks like our video temp dirs
                if os.path.isdir(temp_path):
                    try:
                        # Check if directory contains our video files
                        contents = os.listdir(temp_path)
                        if any(f.endswith(('.mp4', '.mp3', 'concat.txt')) for f in contents):
                            shutil.rmtree(temp_path, ignore_errors=True)
                            orphaned_count += 1
                    except Exception:
                        pass

        if orphaned_count > 0:
            logger.info("Cleaned up orphaned temp directories", count=orphaned_count)

    except Exception as e:
        logger.warning("Error during temp directory cleanup", error=str(e))

    logger.info("Worker shutdown complete")
