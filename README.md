# LLM Chat App

A ChatGPT-like chat application built with FastAPI, PostgreSQL, Redis, and optional LLM integration via llama-cpp-python.

## Features

- 🔐 JWT authentication (access + refresh tokens with 30-day TTL in Redis)
- 🐙 GitHub OAuth login
- 💬 Multi-chat support with message history
- 🤖 LLM integration via llama-cpp-python (graceful mock fallback)
- 🎨 Modern dark-theme SPA frontend
- 🐳 Docker-compose for easy deployment

## Quick Start

### Prerequisites

- Docker & Docker Compose

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

If you use the legacy CLI, this also works:

```bash
docker-compose up --build
```

The app will be available at http://localhost:8000

### Git note

If `git commit` returns `nothing to commit, working tree clean`, create or edit a file first, then run:

```bash
git add <files>
git commit -m "your message"
```

## Manual Setup (Development)

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis 7

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env:
# - Set DATABASE_URL to your PostgreSQL connection
# - Set REDIS_URL to your Redis connection
# - Set SECRET_KEY to a secure random string
# - Optionally configure GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## LLM Integration

To enable real AI responses, download a GGUF model and set the path:

If `wget` is not installed, install it first:

```bash
# macOS (Homebrew)
brew install wget

# Ubuntu/Debian
sudo apt update && sudo apt install -y wget

# Fedora
sudo dnf install -y wget

# Windows (PowerShell with winget)
winget install GNU.Wget
```

```bash
# Example: download a small model
wget https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf

# Set in .env:
LLM_MODEL_PATH=/path/to/model.gguf
```

If you run the app with Docker Compose and the model file is in the project root,
use the container path in `.env`:

```bash
LLM_MODEL_PATH=/app/mistral-7b-v0.1.Q4_K_M.gguf
```

After changing `.env`, restart the app container:

```bash
docker compose restart app
```

### LLM Troubleshooting

If you still get fallback responses ("No LLM model is currently loaded"):

1. Check that `LLM_MODEL_PATH` in `.env` points to a real file.
2. Verify model file size. A valid Mistral 7B Q4_K_M file is around 4 GB, not a few MB.
3. If `wget` created a duplicate like `mistral-7b-v0.1.Q4_K_M.gguf.1`, keep the full-size file and rename it to match `LLM_MODEL_PATH`.
4. Restart app again with `docker compose restart app`.

Without a model, the app returns a helpful fallback message.

## GitHub OAuth Setup

1. Go to GitHub → Settings → Developer Settings → OAuth Apps → New OAuth App
2. Set Homepage URL: `http://localhost:8000`
3. Set Authorization callback URL: `http://localhost:8000/api/auth/github/callback`
4. Copy Client ID and Client Secret to `.env`

Security note: OAuth `state` is used and validated server-side (stored in Redis with short TTL)
to protect the callback flow from CSRF.

## Architecture & Security Notes

- UI mode: SPA (single-page application)
- Backend pattern: MCS (Model-Controller-Service)
	- Models: `app/models/`
	- Controllers (routers): `app/controllers/`
	- Business logic: `app/services/`
- Authentication:
	- Access token: JWT used for protected API routes
	- Refresh token: random token stored in Redis with TTL = 30 days
	- Refresh rotation: old refresh token is deleted on refresh
- GitHub OAuth:
	- Login starts at `/api/auth/github`
	- Callback endpoint is `/api/auth/github/callback`
	- `state` parameter is checked on callback

## API Reference

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh tokens
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user
- `GET /api/auth/github` - Start GitHub OAuth
- `GET /api/auth/github/callback` - GitHub OAuth callback

### Chats
- `GET /api/chats` - List user's chats
- `POST /api/chats` - Create new chat
- `GET /api/chats/{id}` - Get chat with messages
- `PATCH /api/chats/{id}` - Update chat title
- `DELETE /api/chats/{id}` - Delete chat

### Messages
- `GET /api/chats/{id}/messages` - Get messages
- `POST /api/chats/{id}/messages` - Send message (triggers LLM response)

## Architecture

```
MCS (Model-Controller-Service) Architecture:
├── app/models/      - SQLAlchemy ORM models
├── app/schemas/     - Pydantic request/response schemas
├── app/services/    - Business logic
├── app/controllers/ - FastAPI route handlers
└── app/dependencies.py - Shared dependencies (JWT auth)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `SECRET_KEY` | `your-secret-key-...` | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `GITHUB_CLIENT_ID` | `` | GitHub OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | `` | GitHub OAuth App Client Secret |
| `GITHUB_REDIRECT_URI` | `http://localhost:8000/api/auth/github/callback` | GitHub OAuth callback URL |
| `LLM_MODEL_PATH` | `` | Path to GGUF model file |
| `FRONTEND_URL` | `http://localhost:8000` | Frontend URL (for OAuth redirect) |