# Migration from Vercel to Railway

## What Changed

### Removed
- `vercel.json` - Vercel-specific configuration
- `api/rank.py` - Vercel serverless function format

### Added
- `api_server.py` - FastAPI server (works on Railway, Render, Fly.io, etc.)
- `railway.json` - Railway configuration
- `Procfile` - For Heroku/Railway compatibility
- `.railwayignore` - Files to ignore during Railway deployment
- `DEPLOY.md` - Deployment instructions
- `README_RAILWAY.md` - Railway-specific guide

### Updated
- `requirements.txt` - Added `fastapi` and `uvicorn`
- `pages/index.js` - Added environment variable support for API URL
- `.gitignore` - Removed Vercel-specific entries, added Railway

## Why Railway?

1. **No validation issues** - Railway doesn't have the buffer overflow bug we hit with Vercel
2. **Better Python support** - Native Python runtime, no Node.js wrapper
3. **Easier debugging** - Full control over the server
4. **Flexible deployment** - Can deploy as single service or multiple services
5. **Better for ML workloads** - Handles heavy dependencies better

## Quick Start

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize
railway init

# Deploy
railway up
```

## Architecture

### Option 1: Single Service (Simpler)
- Railway runs Python API server
- Next.js can be deployed separately on Vercel/Netlify (just frontend)
- Frontend calls Railway API

### Option 2: Two Services (More Control)
- Service 1: Python API (`api_server.py`)
- Service 2: Next.js frontend
- Both in same Railway project

## Testing Locally

```bash
# Terminal 1: Python API
python api_server.py
# API runs on http://localhost:8000

# Terminal 2: Next.js
npm run dev
# Frontend runs on http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` in `.env.local` for local development.

## Next Steps

1. Test the API server locally: `python api_server.py`
2. Deploy to Railway: `railway up`
3. Update frontend API URL to point to Railway deployment
4. Deploy Next.js (can still use Vercel for frontend-only, or Railway)
