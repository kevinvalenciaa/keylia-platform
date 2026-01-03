"""Initial database schema.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('google_id', sa.String(255), unique=True, nullable=True),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Organization Members table
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(50), default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Brand Kits table
    op.create_table(
        'brand_kits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('agent_name', sa.String(255), nullable=True),
        sa.Column('agent_title', sa.String(255), nullable=True),
        sa.Column('agent_phone', sa.String(50), nullable=True),
        sa.Column('agent_email', sa.String(255), nullable=True),
        sa.Column('brokerage_name', sa.String(255), nullable=True),
        sa.Column('license_number', sa.String(100), nullable=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('headshot_url', sa.Text(), nullable=True),
        sa.Column('primary_color', sa.String(7), default='#2563eb'),
        sa.Column('secondary_color', sa.String(7), default='#1e40af'),
        sa.Column('accent_color', sa.String(7), default='#f59e0b'),
        sa.Column('font_primary', sa.String(100), default='Inter'),
        sa.Column('font_secondary', sa.String(100), default='Playfair Display'),
        sa.Column('social_links', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Property Listings table
    op.create_table(
        'property_listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('address_line1', sa.String(255), nullable=False),
        sa.Column('address_line2', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('neighborhood', sa.String(100), nullable=True),
        sa.Column('listing_status', sa.String(50), default='for_sale', index=True),
        sa.Column('listing_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('bedrooms', sa.SmallInteger(), nullable=True),
        sa.Column('bathrooms', sa.Numeric(3, 1), nullable=True),
        sa.Column('square_feet', sa.Integer(), nullable=True),
        sa.Column('lot_size', sa.String(50), nullable=True),
        sa.Column('year_built', sa.SmallInteger(), nullable=True),
        sa.Column('property_type', sa.String(50), nullable=True),
        sa.Column('features', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('mls_number', sa.String(50), nullable=True),
        sa.Column('target_audience', sa.String(100), nullable=True),
        sa.Column('positioning_notes', sa.Text(), nullable=True),
        sa.Column('open_house_date', sa.Date(), nullable=True),
        sa.Column('open_house_start', sa.Time(), nullable=True),
        sa.Column('open_house_end', sa.Time(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('property_listings.id'), nullable=True),
        sa.Column('brand_kit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brand_kits.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), default='draft', index=True),
        sa.Column('style_settings', postgresql.JSONB(), default=dict),
        sa.Column('voice_settings', postgresql.JSONB(), default=dict),
        sa.Column('infographic_settings', postgresql.JSONB(), default=dict),
        sa.Column('generated_script', postgresql.JSONB(), nullable=True),
        sa.Column('generated_caption', sa.Text(), nullable=True),
        sa.Column('generated_hashtags', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Media Assets table
    op.create_table(
        'media_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False, index=True),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('storage_url', sa.Text(), nullable=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Numeric(10, 2), nullable=True),
        sa.Column('ai_description', sa.Text(), nullable=True),
        sa.Column('ai_tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('ai_quality_score', sa.Numeric(3, 2), nullable=True),
        sa.Column('processing_status', sa.String(50), default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Scenes table
    op.create_table(
        'scenes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence_order', sa.SmallInteger(), nullable=False),
        sa.Column('start_time_ms', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('narration_text', sa.Text(), nullable=True),
        sa.Column('on_screen_text', sa.String(100), nullable=True),
        sa.Column('media_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media_assets.id'), nullable=True),
        sa.Column('camera_movement', postgresql.JSONB(), default=dict),
        sa.Column('transition_type', sa.String(50), default='crossfade'),
        sa.Column('transition_duration_ms', sa.Integer(), default=500),
        sa.Column('overlay_settings', postgresql.JSONB(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Render Jobs table
    op.create_table(
        'render_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('render_type', sa.String(50), default='final'),
        sa.Column('status', sa.String(50), default='queued', index=True),
        sa.Column('progress_percent', sa.SmallInteger(), default=0),
        sa.Column('settings', postgresql.JSONB(), default=dict),
        sa.Column('output_url', sa.Text(), nullable=True),
        sa.Column('output_file_size', sa.BigInteger(), nullable=True),
        sa.Column('subtitle_url', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('worker_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True, nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('plan_name', sa.String(50), nullable=False),
        sa.Column('video_renders_limit', sa.Integer(), nullable=True),
        sa.Column('video_renders_used', sa.Integer(), default=0),
        sa.Column('storage_limit_gb', sa.Integer(), nullable=True),
        sa.Column('storage_used_bytes', sa.BigInteger(), default=0),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Usage Records table
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('usage_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('render_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('render_jobs.id'), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Social Accounts table
    op.create_table(
        'social_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_user_id', sa.String(255), nullable=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_connected', sa.Boolean(), default=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('social_accounts')
    op.drop_table('usage_records')
    op.drop_table('subscriptions')
    op.drop_table('render_jobs')
    op.drop_table('scenes')
    op.drop_table('media_assets')
    op.drop_table('projects')
    op.drop_table('property_listings')
    op.drop_table('brand_kits')
    op.drop_table('organization_members')
    op.drop_table('organizations')
    op.drop_table('users')

