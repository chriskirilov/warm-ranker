# Frontend Setup Instructions

## Railway API URL
Your API is deployed at: **https://romantic-grace-production.up.railway.app**

## Option 1: Local Development

1. Create `.env.local` file (already created):
```
NEXT_PUBLIC_API_URL=https://romantic-grace-production.up.railway.app/api
```

2. Run Next.js locally:
```bash
npm run dev
```

3. Frontend will be at `http://localhost:3000` and will call the Railway API

## Option 2: Deploy Frontend to Railway

1. Add a new service in Railway for the frontend
2. Set build command: `npm run build`
3. Set start command: `npm start`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://romantic-grace-production.up.railway.app/api`

## Option 3: Deploy Frontend to Vercel/Netlify

Since the frontend is just Next.js (no Python), you can deploy it separately:

### Vercel:
```bash
vercel --prod
```
Add environment variable in Vercel dashboard:
- `NEXT_PUBLIC_API_URL=https://romantic-grace-production.up.railway.app/api`

### Netlify:
```bash
netlify deploy --prod
```
Add environment variable in Netlify dashboard:
- `NEXT_PUBLIC_API_URL=https://romantic-grace-production.up.railway.app/api`

## Testing the API

Test the health endpoint:
```bash
curl https://romantic-grace-production.up.railway.app/health
```

Test the ranking endpoint (after API is working):
```bash
curl -X POST https://romantic-grace-production.up.railway.app/api/rank \
  -F "idea=AI tools for marketing" \
  -F "csv=@mock_contacts.csv"
```
