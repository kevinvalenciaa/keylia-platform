"""Celery application configuration."""

from celery import Celery

from app.config import settings

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
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
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

