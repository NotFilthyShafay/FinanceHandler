import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

router = APIRouter()

@router.get("/")
def home():
    # Serve index.html for the root path
    return HTMLResponse(
        content=open("app/public/index.html", encoding="utf-8").read(),
        status_code=200
    )

@router.get("/{file_path:path}")
async def serve_public_file(file_path: str):
    # Construct the full path to the requested file
    full_path = os.path.join("app/public", file_path)
    
    # Check if the file exists
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    
    # If file doesn't exist, return 404
    raise HTTPException(status_code=404, detail="File not found")