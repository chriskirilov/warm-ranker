# Final Railway Setup Instructions

## Current Issue
Railway container doesn't have `python` command, only `python3`. The startup script should handle this, but Railway might need the start command set explicitly.

## Solution: Set Start Command in Railway Dashboard

### Step 1: Go to Railway Dashboard
1. Visit: https://railway.app/project/eab0496e-a04a-4763-91c2-549d673d7437
2. Click on service: `romantic-grace`

### Step 2: Configure Start Command
1. Go to **Settings** tab
2. Scroll to **Deploy** section
3. Find **Start Command** field
4. Set it to: `python3 api_server.py`
5. Click **Save**

### Step 3: Redeploy
1. Go to **Deployments** tab
2. Click **Redeploy** on the latest deployment
3. Or trigger a new deployment by pushing to your repo

## Alternative: Use Railway CLI

If you prefer CLI:
```bash
# This might require Railway API access
railway variables set START_COMMAND="python3 api_server.py"
```

## Files Ready
All code is ready:
- ✅ `api_server.py` - FastAPI server
- ✅ `warm_ranker.py` - Core logic (fixed imports)
- ✅ `Procfile` - Uses startup script
- ✅ `start.sh` - Handles python3/python fallback
- ✅ `requirements.txt` - All dependencies
- ✅ `railway.json` - Configuration

## Test After Deployment

```bash
# Health check
curl https://romantic-grace-production.up.railway.app/health

# Should return: {"status":"healthy"}
```

## If Python Still Not Found

Railway should auto-detect Python from `requirements.txt`. If it doesn't:

1. Check build logs in Railway dashboard
2. Verify `requirements.txt` is in root directory
3. Check if Python buildpack is being used
4. Consider using Railway's Python template instead

## Next Steps After API Works

1. Test API with a CSV file
2. Deploy frontend (see FRONTEND_SETUP.md)
3. Connect frontend to Railway API URL
4. Test end-to-end workflow
