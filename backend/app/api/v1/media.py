"""Media upload endpoints with S3 presigned URL generation."""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.api.v1.projects import get_user_organization_id
from app.config import settings
from app.database import get_db
from app.models.media import MediaAsset
from app.models.user import User

router = APIRouter()


# S3 Client setup
def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )


# Schemas
class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1)
    file_size: int = Field(..., gt=0, le=100_000_000)  # Max 100MB
    file_type: Literal["image", "video", "audio", "logo", "headshot"] = "image"
    category: str | None = None
    property_id: UUID | None = None
    project_id: UUID | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_key: str
    asset_id: UUID
    expires_in: int = 3600


class ConfirmUploadRequest(BaseModel):
    asset_id: UUID
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None


class MediaAssetResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    storage_key: str
    storage_url: str
    thumbnail_url: str | None
    category: str | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    ai_description: str | None
    ai_tags: list[str] | None
    ai_quality_score: float | None
    processing_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    assets: list[MediaAssetResponse]
    total: int
    page: int
    limit: int


# Endpoints
@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    request: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadUrlResponse:
    """
    Generate a presigned URL for uploading a file to S3.

    The client should:
    1. Call this endpoint to get a presigned URL
    2. Upload the file directly to S3 using the presigned URL
    3. Call /confirm to mark the upload as complete
    """
    org_id = await get_user_organization_id(current_user, db)

    # Generate unique storage key
    asset_id = uuid4()
    timestamp = datetime.utcnow().strftime("%Y/%m/%d")
    file_ext = request.filename.rsplit(".", 1)[-1] if "." in request.filename else ""

    # Structure: org_id/property_id/timestamp/asset_id.ext
    if request.property_id:
        storage_key = f"{org_id}/properties/{request.property_id}/{timestamp}/{asset_id}.{file_ext}"
    elif request.project_id:
        storage_key = f"{org_id}/projects/{request.project_id}/{timestamp}/{asset_id}.{file_ext}"
    else:
        storage_key = f"{org_id}/uploads/{timestamp}/{asset_id}.{file_ext}"

    # Generate presigned URL
    s3_client = get_s3_client()
    try:
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": storage_key,
                "ContentType": request.content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}",
        )

    # Create pending media asset record
    storage_url = f"{settings.S3_BUCKET_URL}/{storage_key}" if settings.S3_BUCKET_URL else f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{storage_key}"

    media_asset = MediaAsset(
        id=asset_id,
        organization_id=org_id,
        project_id=request.project_id,
        filename=request.filename,
        file_type=request.file_type,
        mime_type=request.content_type,
        file_size_bytes=request.file_size,
        storage_key=storage_key,
        storage_url=storage_url,
        category=request.category,
        processing_status="uploading",
    )

    db.add(media_asset)
    await db.commit()

    return UploadUrlResponse(
        upload_url=presigned_url,
        storage_key=storage_key,
        asset_id=asset_id,
        expires_in=3600,
    )


@router.post("/confirm", response_model=MediaAssetResponse)
async def confirm_upload(
    request: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaAssetResponse:
    """
    Confirm that a file has been uploaded to S3.

    This should be called after the client successfully uploads
    the file to the presigned URL.
    """
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == request.asset_id,
            MediaAsset.organization_id == org_id,
        )
    )
    media_asset = result.scalar_one_or_none()

    if not media_asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if media_asset.processing_status != "uploading":
        raise HTTPException(
            status_code=400,
            detail=f"Asset is in '{media_asset.processing_status}' state, expected 'uploading'",
        )

    # Verify the file exists in S3
    s3_client = get_s3_client()
    try:
        s3_client.head_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=media_asset.storage_key,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(
                status_code=400,
                detail="File not found in storage. Please upload the file first.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify upload: {str(e)}",
        )

    # Update asset with metadata
    media_asset.processing_status = "completed"
    if request.width:
        media_asset.width = request.width
    if request.height:
        media_asset.height = request.height
    if request.duration_seconds:
        media_asset.duration_seconds = request.duration_seconds

    await db.commit()
    await db.refresh(media_asset)

    return MediaAssetResponse.model_validate(media_asset)


@router.get("", response_model=MediaListResponse)
async def list_media(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    file_type: str | None = None,
    project_id: UUID | None = None,
    category: str | None = None,
) -> MediaListResponse:
    """List all media assets for the current user's organization."""
    org_id = await get_user_organization_id(current_user, db)

    from sqlalchemy import func

    # Build query
    query = select(MediaAsset).where(
        MediaAsset.organization_id == org_id,
        MediaAsset.processing_status == "completed",
    )

    if file_type:
        query = query.where(MediaAsset.file_type == file_type)
    if project_id:
        query = query.where(MediaAsset.project_id == project_id)
    if category:
        query = query.where(MediaAsset.category == category)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    query = query.order_by(MediaAsset.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    assets = result.scalars().all()

    return MediaListResponse(
        assets=[MediaAssetResponse.model_validate(a) for a in assets],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{asset_id}", response_model=MediaAssetResponse)
async def get_media_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaAssetResponse:
    """Get a media asset by ID."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == org_id,
        )
    )
    media_asset = result.scalar_one_or_none()

    if not media_asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    return MediaAssetResponse.model_validate(media_asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_asset(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a media asset from S3 and database."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == org_id,
        )
    )
    media_asset = result.scalar_one_or_none()

    if not media_asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    # Delete from S3
    s3_client = get_s3_client()
    try:
        s3_client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=media_asset.storage_key,
        )
        # Also delete thumbnail if exists
        if media_asset.thumbnail_url:
            thumbnail_key = media_asset.thumbnail_url.split("/")[-1]
            s3_client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=f"thumbnails/{thumbnail_key}",
            )
    except ClientError:
        pass  # Continue with database deletion even if S3 delete fails

    await db.delete(media_asset)
    await db.commit()


@router.post("/{asset_id}/download-url")
async def get_download_url(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    expires_in: int = Query(3600, ge=60, le=86400),
) -> dict:
    """Get a presigned download URL for a media asset."""
    org_id = await get_user_organization_id(current_user, db)

    result = await db.execute(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == org_id,
        )
    )
    media_asset = result.scalar_one_or_none()

    if not media_asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    s3_client = get_s3_client()
    try:
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": media_asset.storage_key,
                "ResponseContentDisposition": f'attachment; filename="{media_asset.filename}"',
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate download URL: {str(e)}",
        )

    return {
        "download_url": download_url,
        "expires_in": expires_in,
        "filename": media_asset.filename,
    }
