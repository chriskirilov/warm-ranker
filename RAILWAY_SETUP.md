# Railway Deployment Setup

## Step 1: Login to Railway
You need to login first. Run this command in your terminal:
```bash
railway login
```
This will open a browser for authentication.

## Step 2: Link to Your Project
Once logged in, link to your existing project:
```bash
railway link --project 08dd20fe-1b83-45d2-b92e-50e97a890c62
```

## Step 3: Set Environment Variables
Set any required environment variables:
```bash
railway variables set WANDB_API_KEY=your_key_here
railway variables set PORT=8000
```

## Step 4: Deploy
Deploy your application:
```bash
railway up
```

## Alternative: Deploy via Railway Dashboard
1. Go to https://railway.app
2. Open your project (ID: 08dd20fe-1b83-45d2-b92e-50e97a890c62)
3. Connect your GitHub repo or upload files
4. Railway will auto-detect Python and run `api_server.py`
5. Add environment variables in the dashboard
6. Deploy!

## Quick Deploy Command (after login)
```bash
railway login && railway link --project 08dd20fe-1b83-45d2-b92e-50e97a890c62 && railway up
```
