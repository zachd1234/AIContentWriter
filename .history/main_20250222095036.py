from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from src.api_handler import ContentAPIHandler

app = FastAPI(
    title="Content Generation API",
    description="API for generating blog posts with media and internal links",
    version="1.0.0"
)

class KeywordRequest(BaseModel):
    keyword: str

@app.post("/generate")
async def generate_post(keyword: str):
    """
    Generate a complete blog post with media and internal links
    """
    try:
        handler = ContentAPIHandler()
        result = await handler.generate_complete_post(keyword)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate content")
            
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "AI Blog Writer API is running"}