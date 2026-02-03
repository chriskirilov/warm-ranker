# Dockerfile Deployment

## What Changed

Created a `Dockerfile` to ensure Python is properly available:
- Uses official `python:3.12-slim` image
- Installs all dependencies from `requirements.txt`
- Exposes port 8000
- Runs `python api_server.py` (Python 3.12 has `python` command)

Updated `railway.json` to use Docker builder instead of Nixpacks:
- Changed `builder: "NIXPACKS"` → `builder: "DOCKERFILE"`

## Why This Should Work

1. **Guaranteed Python**: Docker image has Python pre-installed
2. **No detection issues**: Railway doesn't need to detect Python
3. **Consistent environment**: Same Python version every time
4. **Simpler**: No need for Procfile or startup scripts

## Current Status

- ✅ Dockerfile created
- ✅ railway.json updated to use Docker
- ⏳ Deployment in progress

## Test After Deployment

```bash
# Health check
curl https://romantic-grace-production.up.railway.app/health

# Should return: {"status":"healthy"}
```

## If Still Not Working

Check Railway dashboard build logs to see if:
1. Dockerfile is being detected
2. Build is completing successfully
3. Container is starting correctly

If Railway still uses Nixpacks, you may need to:
1. Go to Railway dashboard
2. Service Settings → Deploy
3. Set Builder to "Dockerfile" manually
