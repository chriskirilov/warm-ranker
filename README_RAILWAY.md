# Deploying Warm Ranker on Railway

## Option 1: Single Service (Recommended for simplicity)

Railway can auto-detect and run both Next.js and Python. However, for better control, we'll deploy the Python API separately.

## Option 2: Two Services (Recommended)

### Service 1: Python API
1. Create a new Railway project
2. Connect your GitHub repo
3. Railway will auto-detect Python
4. Set the start command: `python api_server.py`
5. Add environment variables:
   - `WANDB_API_KEY` (if needed)
   - `PORT` (Railway sets this automatically)
   - Redis URL (if using external Redis)
   - Browserbase API key

### Service 2: Next.js Frontend
1. Create another service in the same project
2. Set root directory to project root
3. Set build command: `npm run build`
4. Set start command: `npm start`
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = URL of your Python API service

## Quick Start

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Deploy: `railway up`

## Alternative: Render.com

Render is another great option:
- Create a Web Service for Python API
- Create a Static Site for Next.js (or another Web Service)
- Similar setup to Railway

## Alternative: Fly.io

Fly.io is also excellent:
- `fly launch` to initialize
- Supports both Python and Node.js
- Good for global distribution
