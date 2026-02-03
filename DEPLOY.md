# Deployment Guide - Railway

## Quick Start

### 1. Install Railway CLI
```bash
npm i -g @railway/cli
```

### 2. Login to Railway
```bash
railway login
```

### 3. Initialize Project
```bash
railway init
```

### 4. Deploy
```bash
railway up
```

## Two-Service Setup (Recommended)

### Service 1: Python API

1. In Railway dashboard, create a new service
2. Connect your GitHub repo
3. Railway will auto-detect Python from `requirements.txt`
4. Set environment variables:
   - `PORT` (auto-set by Railway)
   - `WANDB_API_KEY` (if needed)
   - Any other API keys

5. The API will be available at: `https://your-api-service.railway.app`

### Service 2: Next.js Frontend

1. Create another service in the same Railway project
2. Set build command: `npm run build`
3. Set start command: `npm start`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://your-api-service.railway.app/api`

## Single Service Alternative

Railway can also run both in one service, but you'll need a custom start script.

## Alternative Platforms

### Render.com
1. Create a Web Service
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt && python api_server.py`
4. Start command: `python api_server.py`

### Fly.io
1. Install: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Deploy: `fly deploy`

### DigitalOcean App Platform
1. Create new app from GitHub
2. Select Python
3. Set run command: `python api_server.py`
4. Add environment variables

## Environment Variables Needed

- `WANDB_API_KEY` - Weights & Biases API key
- `PORT` - Server port (usually auto-set)
- Redis connection (if using external Redis)
- Browserbase API key

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
python api_server.py

# In another terminal, run Next.js
npm run dev
```

The API will be at `http://localhost:8000` and Next.js at `http://localhost:3000`
