"""
FastAPI server for warm_ranker API
Deployable on Railway, Render, Fly.io, etc.
"""
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
import tempfile

# Import the warm_ranker logic
from warm_ranker import main

app = FastAPI(title="Warm Ranker API")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Warm Ranker API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/rank")
async def rank_contacts(
    idea: str = Form(...),
    csv: UploadFile = File(...)
):
    """
    Rank contacts based on an idea
    """
    temp_path = None
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            content = await csv.read()
            tmp_file.write(content)
            temp_path = tmp_file.name
        
        # Process with warm_ranker
        result = main(idea, temp_path)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"Error: {error_msg}", file=sys.stderr)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg}
        )
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
