# ReelEstate Studio - System & Architecture Design

## 1. Technology Stack

### Frontend
| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | **Next.js 14** (App Router) | SSR for SEO, excellent DX, React ecosystem |
| Language | **TypeScript** | Type safety, better tooling |
| Styling | **Tailwind CSS** + **shadcn/ui** | Rapid UI development, consistent design system |
| State | **Zustand** | Lightweight, simple global state |
| Forms | **React Hook Form** + **Zod** | Type-safe forms with validation |
| Media | **UploadThing** or **S3 presigned URLs** | Direct-to-storage uploads |
| Video Preview | **Video.js** | Robust video player |
| Charts | **Recharts** | Analytics visualizations |

### Backend
| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | **FastAPI** (Python) | Async, fast, excellent for AI workloads |
| Language | **Python 3.11+** | AI/ML ecosystem, video processing libraries |
| Auth | **NextAuth.js** (frontend) + **JWT** | OAuth support, session management |
| Validation | **Pydantic v2** | Request/response validation |
| ORM | **SQLAlchemy 2.0** + **Alembic** | Async support, migrations |

### Database & Storage
| Layer | Technology | Rationale |
|-------|------------|-----------|
| Primary DB | **PostgreSQL 15** | Relational data, JSONB for flexibility |
| Cache | **Redis** | Session cache, job queue, rate limiting |
| Object Storage | **AWS S3** / **Cloudflare R2** | Media files, cost-effective |
| CDN | **CloudFront** / **Cloudflare** | Fast media delivery |

### Job Queue & Workers
| Layer | Technology | Rationale |
|-------|------------|-----------|
| Queue | **Redis** + **Celery** / **Bull** | Reliable job processing |
| Workers | **Python Celery workers** | CPU/GPU video processing |
| Orchestration | **Docker** + **Kubernetes** (production) | Scalable worker pools |

### AI/ML Services
| Capability | Provider Options | Rationale |
|------------|------------------|-----------|
| Script Generation | **OpenAI GPT-4** / **Claude** | High-quality copy |
| Text-to-Speech | **ElevenLabs** / **OpenAI TTS** | Natural voices |
| Talking Avatar | **HeyGen** / **Synthesia** / **D-ID** | Realistic avatars |
| Image Analysis | **OpenAI Vision** / **Claude Vision** | Photo understanding |
| Music | **Licensed library** (Epidemic Sound, Artlist) | Royalty-free |
| **Video Generation** | **fal.ai** (Kling, Luma, Runway, SVD) | AI-powered image-to-video |

### Video Processing
| Capability | Technology | Rationale |
|------------|------------|-----------|
| **AI Video Generation** | **fal.ai** | Transform photos to cinematic clips with AI motion |
| Composition | **FFmpeg** + **MoviePy** | Frame-accurate editing |
| Motion Graphics | **Remotion** (React) or **Motion Canvas** | Programmatic animations |
| Image Processing | **Pillow** + **OpenCV** | Cropping, effects |
| Rendering | **GPU-accelerated FFmpeg** | Fast encoding |

### fal.ai Video Models Used
| Model | Use Case | Duration |
|-------|----------|----------|
| **Kling Standard** | Primary property tours | 5-10 sec |
| **Kling Pro** | High-quality luxury listings | 5-10 sec |
| **Luma Dream Machine** | Smooth cinematic motion | 5 sec |
| **Runway Gen-3** | Text-guided generation | 5-10 sec |
| **Fast SVD-LCM** | Quick previews | 2-4 sec |
| **MiniMax** | Extended clips | Up to 6 sec |

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Next.js Frontend (Vercel)                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │   │
│  │  │  Dashboard  │ │   Wizard    │ │   Editor    │ │     Library     │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTPS
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Backend (Railway/Render)                   │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐ │   │
│  │  │    Auth    │ │  Projects  │ │     AI     │ │      Billing       │ │   │
│  │  │   Module   │ │   Module   │ │   Module   │ │      Module        │ │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│              │                  │                    │                       │
└──────────────┼──────────────────┼────────────────────┼──────────────────────┘
               │                  │                    │
               ▼                  ▼                    ▼
┌──────────────────────┐ ┌─────────────────┐ ┌─────────────────────────────────┐
│   DATA LAYER         │ │  STORAGE LAYER  │ │        QUEUE LAYER              │
├──────────────────────┤ ├─────────────────┤ ├─────────────────────────────────┤
│                      │ │                 │ │                                 │
│  ┌────────────────┐  │ │ ┌─────────────┐ │ │  ┌─────────────────────────┐   │
│  │   PostgreSQL   │  │ │ │     S3      │ │ │  │     Redis Queue         │   │
│  │    (Neon/RDS)  │  │ │ │ (R2/Spaces) │ │ │  │    (Upstash/AWS)        │   │
│  └────────────────┘  │ │ └─────────────┘ │ │  └───────────┬─────────────┘   │
│                      │ │       │         │ │              │                 │
│  ┌────────────────┐  │ │       ▼         │ │              ▼                 │
│  │     Redis      │  │ │ ┌─────────────┐ │ │  ┌─────────────────────────┐   │
│  │    (Cache)     │  │ │ │     CDN     │ │ │  │    Celery Workers       │   │
│  └────────────────┘  │ │ │ (Cloudflare)│ │ │  │    (GPU Instances)      │   │
│                      │ │ └─────────────┘ │ │  └───────────┬─────────────┘   │
└──────────────────────┘ └─────────────────┘ │              │                 │
                                             └──────────────┼─────────────────┘
                                                            │
                                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI SERVICES LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────────┐  │
│  │   OpenAI /    │ │  ElevenLabs   │ │    HeyGen     │ │   Video Proc    │  │
│  │    Claude     │ │     TTS       │ │    Avatar     │ │    (FFmpeg)     │  │
│  │  (LLM + Vision)│ │              │ │               │ │                 │  │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Architecture

### 3.1 Frontend Architecture

```
frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth-related routes
│   │   ├── login/
│   │   ├── signup/
│   │   └── onboarding/
│   ├── (dashboard)/              # Authenticated routes
│   │   ├── dashboard/
│   │   ├── projects/
│   │   │   ├── new/              # Project wizard
│   │   │   └── [id]/             # Project details/editor
│   │   ├── library/
│   │   ├── calendar/
│   │   ├── analytics/
│   │   └── settings/
│   ├── api/                      # API routes (auth, webhooks)
│   └── layout.tsx
├── components/
│   ├── ui/                       # shadcn/ui components
│   ├── forms/                    # Form components
│   ├── wizard/                   # Project wizard steps
│   ├── editor/                   # Storyboard editor
│   └── common/                   # Shared components
├── lib/
│   ├── api/                      # API client
│   ├── hooks/                    # Custom hooks
│   ├── utils/                    # Utilities
│   └── validations/              # Zod schemas
└── stores/                       # Zustand stores
```

### 3.2 Backend Architecture

```
backend/
├── app/
│   ├── main.py                   # FastAPI app entry
│   ├── config.py                 # Settings & env vars
│   ├── database.py               # DB connection
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── brand_kits.py
│   │   │   ├── projects.py
│   │   │   ├── scenes.py
│   │   │   ├── media.py
│   │   │   ├── render_jobs.py
│   │   │   ├── ai.py
│   │   │   └── billing.py
│   │   └── deps.py               # Dependencies
│   ├── models/                   # SQLAlchemy models
│   ├── schemas/                  # Pydantic schemas
│   ├── services/                 # Business logic
│   │   ├── ai/
│   │   │   ├── script_generator.py
│   │   │   ├── shot_planner.py
│   │   │   ├── layout_generator.py
│   │   │   └── voice_generator.py
│   │   ├── video/
│   │   │   ├── compositor.py
│   │   │   ├── effects.py
│   │   │   └── renderer.py
│   │   └── social/
│   │       └── meta_publisher.py
│   ├── workers/                  # Celery tasks
│   │   ├── render_video.py
│   │   ├── render_infographic.py
│   │   └── generate_avatar.py
│   └── core/
│       ├── security.py
│       ├── storage.py
│       └── exceptions.py
├── migrations/                   # Alembic migrations
└── tests/
```

---

## 4. Data Flow Diagrams

### 4.1 Video Generation Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        VIDEO GENERATION PIPELINE                          │
└──────────────────────────────────────────────────────────────────────────┘

User Input                 AI Processing               Rendering
─────────                  ─────────────               ─────────

┌─────────────┐           ┌─────────────┐           ┌─────────────┐
│   Photos    │──────────▶│ Image       │──────────▶│ Shot Plan   │
│   (5-40)    │           │ Analysis    │           │ Generation  │
└─────────────┘           │ (GPT-4V)    │           │             │
                          └─────────────┘           └──────┬──────┘
┌─────────────┐                                            │
│  Property   │──────────▶┌─────────────┐                  │
│  Details    │           │   Script    │                  │
└─────────────┘           │ Generation  │                  │
                          │  (GPT-4)    │                  │
┌─────────────┐           └──────┬──────┘                  │
│   Style     │                  │                         │
│ Preferences │                  ▼                         ▼
└─────────────┘           ┌─────────────┐           ┌─────────────┐
                          │ Storyboard  │◀──────────│   Scenes    │
                          │   Preview   │           │   Matched   │
                          └──────┬──────┘           └─────────────┘
                                 │
                    User Approval│
                                 ▼
                          ┌─────────────┐           ┌─────────────┐
                          │    TTS      │──────────▶│   Audio     │
                          │ Generation  │           │   Track     │
                          │ (ElevenLabs)│           └──────┬──────┘
                          └─────────────┘                  │
                                                           ▼
┌─────────────┐                                     ┌─────────────┐
│   Music     │────────────────────────────────────▶│   Video     │
│   Track     │                                     │ Composition │
└─────────────┘                                     │  (FFmpeg)   │
                                                    └──────┬──────┘
┌─────────────┐                                            │
│  Captions   │────────────────────────────────────────────┤
│  Overlays   │                                            │
└─────────────┘                                            ▼
                                                    ┌─────────────┐
                                                    │   Final     │
                                                    │   Export    │
                                                    │ (MP4 + SRT) │
                                                    └─────────────┘
```

### 4.2 Render Job Queue Flow

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           RENDER JOB LIFECYCLE                             │
└───────────────────────────────────────────────────────────────────────────┘

 Frontend                    API                     Queue                Workers
 ────────                    ───                     ─────                ───────

┌─────────┐               ┌─────────┐             ┌─────────┐
│ Submit  │──────────────▶│ Create  │────────────▶│ Enqueue │
│  Job    │               │  Job    │             │  Job    │
└─────────┘               │ Record  │             └────┬────┘
                          └─────────┘                  │
     ▲                         │                       │
     │                         ▼                       ▼
     │                   ┌──────────┐           ┌─────────────┐
     │                   │ WebSocket│◀──────────│   Worker    │
     │                   │  Update  │           │   Claims    │
     │                   └──────────┘           │    Job      │
     │                         │                └──────┬──────┘
     │                         │                       │
┌────┴────┐                    │                       ▼
│ Progress│◀───────────────────┘                ┌─────────────┐
│  Bar    │                                     │  Process:   │
└─────────┘                                     │  1. Assets  │
                                                │  2. AI Gen  │
     ▲                   ┌──────────┐           │  3. Render  │
     │                   │  Update  │◀──────────│  4. Upload  │
     │                   │  Status  │           └──────┬──────┘
     │                   └──────────┘                  │
     │                         │                       │
┌────┴────┐                    │                       ▼
│ Complete│◀───────────────────┘                ┌─────────────┐
│  + URL  │                                     │   Mark      │
└─────────┘                                     │  Complete   │
                                                └─────────────┘
```

---

## 5. Infrastructure & Deployment

### Development Environment
```yaml
# docker-compose.dev.yml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: ["./frontend:/app"]
    
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./backend:/app"]
    depends_on: [postgres, redis]
    
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    
  worker:
    build: ./backend
    command: celery -A app.workers worker
    depends_on: [postgres, redis]
```

### Production Environment
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │   Cloudflare    │
                         │      DNS        │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
           ┌─────────────────┐        ┌─────────────────┐
           │     Vercel      │        │  Railway/Render │
           │   (Frontend)    │        │    (Backend)    │
           │   Auto-scale    │        │    Auto-scale   │
           └─────────────────┘        └────────┬────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
                    ▼                          ▼                      ▼
           ┌─────────────────┐        ┌─────────────────┐    ┌─────────────────┐
           │      Neon       │        │    Upstash      │    │   Cloudflare    │
           │   PostgreSQL    │        │     Redis       │    │       R2        │
           │   Serverless    │        │   Serverless    │    │    Storage      │
           └─────────────────┘        └────────┬────────┘    └─────────────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │   GPU Workers   │
                                      │  (Modal/Replicate│
                                      │   or RunPod)    │
                                      └─────────────────┘
```

### Scaling Strategy

| Component | Scaling Approach |
|-----------|------------------|
| Frontend | Vercel Edge (automatic) |
| API | Horizontal pod autoscaling (CPU/memory) |
| Workers | Queue depth-based autoscaling |
| Database | Neon autoscaling or RDS read replicas |
| Storage | CDN caching, tiered storage |

---

## 6. Security Architecture

### Authentication Flow
```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Client   │────▶│  NextAuth  │────▶│   OAuth    │────▶│   Google   │
│            │◀────│  Session   │◀────│  Callback  │◀────│   /Email   │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
      │                  │
      │                  ▼
      │            ┌────────────┐
      │            │    JWT     │
      │            │   Token    │
      │            └─────┬──────┘
      │                  │
      │                  ▼
      │            ┌────────────┐     ┌────────────┐
      └───────────▶│  FastAPI   │────▶│  Validate  │
                   │    API     │     │    JWT     │
                   └────────────┘     └────────────┘
```

### Data Isolation
- Row-level security in PostgreSQL
- All queries scoped by `organization_id`
- S3 bucket policies per organization
- API middleware enforces tenant context

### Secrets Management
- Environment variables for configuration
- AWS Secrets Manager / Doppler for production
- Separate secrets per environment

