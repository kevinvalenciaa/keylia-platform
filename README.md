# ReelEstate Studio

**AI-powered content creation platform for real estate agents.**

Transform property photos into scroll-stopping social media videos and graphics in minutes—no editing skills required.

## Features

### 🎬 Listing Tour Videos
- Cinematic property tours from still photos
- Ken Burns effect with smooth pans and zooms
- AI-generated voiceover narration
- Multiple music and tone options

### 🎤 Promo Videos
- AI avatar from headshot photo
- Selfie video enhancement
- Automatic B-roll insertion
- Dynamic captions

### 📊 Infographics
- Branded graphics and carousels
- Single card or multi-slide
- Static or animated
- Open house announcements

## Tech Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Component library
- **Zustand** - State management
- **React Query** - Server state management

### Backend
- **FastAPI** - Python async API framework
- **SQLAlchemy 2.0** - Async ORM
- **PostgreSQL** - Primary database
- **Redis** - Caching and job queue
- **Celery** - Background task processing

### AI/ML
- **OpenAI GPT-4** - Script generation
- **fal.ai** - AI video generation (Kling, Luma, Runway, SVD)
- **ElevenLabs** - Text-to-speech
- **HeyGen** - Avatar generation
- **FFmpeg** - Video composition

### Infrastructure
- **Docker** - Containerization
- **AWS S3** - Media storage
- **Stripe** - Payments

## Quick Start

### Automated Setup (Recommended)

```bash
# Run the setup script
./scripts/setup.sh

# Start all services
./scripts/start-dev.sh
```

### Manual Setup

For detailed step-by-step instructions, see **[SETUP.md](./SETUP.md)**.

**Quick commands:**

1. **Create Supabase project** (recommended)
   - Go to https://supabase.com
   - Create project and get connection string
   - See [docs/SUPABASE_SETUP.md](./docs/SUPABASE_SETUP.md) for details

2. **Start Redis** (or use Upstash Cloud)
   ```bash
   docker-compose up -d redis
   # OR use Upstash Redis Cloud (free tier)
   ```

3. **Setup backend**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   cp .env.example .env  # Edit with your API keys
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

4. **Setup frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local  # Edit with your settings
   npm run dev
   ```

5. **Start worker** (new terminal)
   ```bash
   cd backend
   source venv/bin/activate
   celery -A app.workers.celery_app worker --loglevel=info
   ```

### Prerequisites
- Node.js 20+
- Python 3.11+
- **Supabase account** (free tier - recommended) OR PostgreSQL 15+
- Redis 7+ (or Docker, or Upstash Cloud)
- FFmpeg (for video processing)

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

## Project Structure

```
keylia-platform/
├── docs/                    # Documentation
│   ├── 01-PRODUCT-SPECIFICATION.md
│   ├── 02-SYSTEM-ARCHITECTURE.md
│   ├── 03-DATA-MODEL-API.md
│   ├── 04-UX-FLOWS-SCREENS.md
│   └── 05-AI-PROMPTING-PIPELINES.md
├── frontend/                # Next.js frontend
│   ├── app/                 # App Router pages
│   ├── components/          # React components
│   ├── lib/                 # Utilities
│   └── stores/              # Zustand stores
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   └── workers/        # Celery tasks
│   └── migrations/         # Alembic migrations
├── docker-compose.yml
└── README.md
```

## API Overview

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PATCH /api/v1/projects/{id}` - Update project

### AI Generation
- `POST /api/v1/ai/generate-script` - Generate video script
- `POST /api/v1/ai/generate-caption` - Generate social caption
- `POST /api/v1/ai/generate-shot-plan` - Generate camera movements

### Rendering
- `POST /api/v1/projects/{id}/renders` - Start render job
- `GET /api/v1/renders/{id}` - Get render status

## Environment Variables

### Backend
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS |
| `FAL_KEY` | fal.ai API key for video generation |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 |
| `STRIPE_SECRET_KEY` | Stripe API key |

### Frontend
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXTAUTH_SECRET` | NextAuth.js secret |
| `GOOGLE_CLIENT_ID` | Google OAuth credentials |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved.

## Support

- Documentation: `/docs`
- Email: support@reelestate.studio

