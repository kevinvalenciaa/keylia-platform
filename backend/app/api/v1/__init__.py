"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import auth, users, brand_kits, properties, projects, media, ai, render_jobs, billing, tour_videos

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(brand_kits.router, prefix="/brand-kits", tags=["Brand Kits"])
router.include_router(properties.router, prefix="/properties", tags=["Properties"])
router.include_router(projects.router, prefix="/projects", tags=["Projects"])
router.include_router(media.router, prefix="/media", tags=["Media"])
router.include_router(ai.router, prefix="/ai", tags=["AI"])
router.include_router(render_jobs.router, prefix="/renders", tags=["Render Jobs"])
router.include_router(billing.router, prefix="/billing", tags=["Billing"])
router.include_router(tour_videos.router, prefix="/tour-videos", tags=["Tour Videos"])

