# Keylia

**AI-powered content creation platform for real estate agents.**

Transform property photos into scroll-stopping social media videos and graphics in minutes, with no editing skills required.

## Overview

Keylia is a full-stack SaaS application that leverages multiple AI services to automate real estate content creation. The platform handles the complete pipeline from photo upload to final video delivery, including AI script generation, text-to-speech voiceover, image-to-video transformation, and video composition.

## Features

### Listing Tour Videos
- Cinematic property tours generated from still photos
- Ken Burns effect with smooth pans and zooms via fal.ai
- AI-generated voiceover narration using ElevenLabs
- Multiple music and tone options

### Promo Videos
- AI avatar generation from headshot photos
- Selfie video enhancement
- Automatic B-roll insertion
- Dynamic captions

### Infographics
- Branded graphics and carousels
- Single card or multi-slide formats
- Static or animated output
- Open house announcements

## Architecture

```
                    +------------------+
                    |    Next.js 14    |
                    |    (Frontend)    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |      tRPC        |
                    |   (Type-safe)    |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                                       |
+--------v---------+                   +---------v--------+
|     FastAPI      |                   |     Supabase     |
|    (Backend)     |                   |   (Auth + DB)    |
+--------+---------+                   +------------------+
         |
+--------v---------+
|      Celery      |
|  (Task Queue)    |
+--------+---------+
         |
    +----+----+----+----+
    |    |    |    |    |
    v    v    v    v    v
  fal.ai  ElevenLabs  FFmpeg  S3
```

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| TypeScript | Type-safe development |
| Tailwind CSS | Utility-first styling |
| shadcn/ui | Component library |
| Zustand | Client state management |
| React Query | Server state management |
| tRPC | End-to-end type-safe API |

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Python async API framework |
| SQLAlchemy 2.0 | Async ORM with PostgreSQL |
| PostgreSQL | Primary database |
| Redis | Caching and job queue |
| Celery | Background task processing |
| Pydantic | Request/response validation |

### AI/ML Services
| Service | Purpose |
|---------|---------|
| Anthropic Claude | Script generation |
| fal.ai | AI video generation (Kling, Veo, Minimax) |
| ElevenLabs | Text-to-speech voiceover |
| HeyGen | Avatar video generation |
| FFmpeg | Video composition and encoding |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Supabase | Authentication and managed PostgreSQL |
| AWS S3 | Media storage |
| Stripe | Payment processing |

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- Redis 7+ (or Docker)
- FFmpeg (for video processing)
- Supabase account (free tier available)

### Quick Start

```bash
# Clone and setup
./scripts/setup.sh

# Start all services
./scripts/start-dev.sh
```

### Manual Setup

1. **Database Setup** (Supabase recommended)
   ```bash
   # Create project at https://supabase.com
   # Run migrations from supabase/migrations/
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   cp .env.example .env  # Configure API keys
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local  # Configure settings
   npm run dev
   ```

4. **Worker Setup** (new terminal)
   ```bash
   cd backend
   source venv/bin/activate
   celery -A app.workers.celery_app worker --loglevel=info
   ```

### Access Points
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/api/docs |

## Project Structure

```
keylia-platform/
├── frontend/                 # Next.js 14 application
│   ├── app/                  # App Router pages
│   │   ├── (auth)/           # Authentication pages
│   │   ├── (dashboard)/      # Protected dashboard
│   │   └── api/              # API routes
│   ├── components/           # React components
│   ├── server/               # tRPC routers
│   └── lib/                  # Utilities
│
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/v1/           # REST endpoints
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   └── workers/          # Celery tasks
│   └── migrations/           # Alembic migrations
│
├── supabase/                 # Database migrations
├── scripts/                  # Development scripts
└── docker-compose.yml        # Local development stack
```

## API Reference

### Authentication
```
POST /api/v1/auth/register    # User registration
POST /api/v1/auth/login       # User login
POST /api/v1/auth/refresh     # Token refresh
```

### Projects
```
GET    /api/v1/projects       # List projects
POST   /api/v1/projects       # Create project
GET    /api/v1/projects/{id}  # Get project
PATCH  /api/v1/projects/{id}  # Update project
DELETE /api/v1/projects/{id}  # Delete project
```

### AI Generation
```
POST /api/v1/ai/generate-script     # Generate video script
POST /api/v1/ai/generate-caption    # Generate social caption
POST /api/v1/ai/generate-shot-plan  # Generate camera movements
```

### Rendering
```
POST /api/v1/projects/{id}/renders  # Start render job
GET  /api/v1/renders/{id}           # Get render status
```

## Environment Variables

### Backend (.env)
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS |
| `FAL_KEY` | fal.ai API key for video generation |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 |
| `STRIPE_SECRET_KEY` | Stripe API key |

### Frontend (.env.local)
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |

## Development

### Code Quality
- **TypeScript** with strict mode enabled
- **Ruff** for Python linting (line-length: 100)
- **MyPy** for Python type checking
- **ESLint** for JavaScript/TypeScript linting

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

## Deployment

The application is containerized and can be deployed to any Docker-compatible environment:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or deploy individual services
docker build -t keylia-backend ./backend
docker build -t keylia-frontend ./frontend
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved.

## Contact

- Documentation: `/docs`
- Email: support@keylia.io
