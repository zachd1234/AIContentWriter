from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import asyncio
from src.api_handler import ContentAPIHandler
import os
from src.backlink_agent.control_panel import create_default_control_panel

app = FastAPI(
    title="Content Generation API",
    description="API for generating blog posts with media and internal links",
    version="1.0.0"
)

API_KEY = os.getenv("API_KEY")

class KeywordRequest(BaseModel):
    keyword: str

class OutreachSetupRequest(BaseModel):
    site_id: int

class OutreachCampaignRequest(BaseModel):
    site_id: int

@app.post("/generate")
async def generate_post(keyword: str, base_url: str, site_id: int, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    """
    Generate a complete blog post with media and internal links, then run outreach campaign
    """
    try:
        # Generate the post
        handler = ContentAPIHandler()
        result = await handler.generate_complete_post(keyword, base_url)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate content")
        
        # Run outreach campaign after successful post generation
        try:
            control_panel = create_default_control_panel()
            outreach_result = control_panel.run_outreach_campaign(site_id)
            
            # Add outreach result to the response
            return {
                "status": "success",
                "data": result,
                "outreach": {
                    "status": "success",
                    "data": outreach_result
                }
            }
        except Exception as e:
            # If outreach fails, still return the post but with error info
            return {
                "status": "success",
                "data": result,
                "outreach": {
                    "status": "error",
                    "message": str(e)
                }
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

@app.post("/run-outreach-campaign")
async def run_outreach_campaign(request: OutreachCampaignRequest, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    """
    Run an outreach campaign for the specified site ID
    """
    try:
        control_panel = create_default_control_panel()
        result = control_panel.run_outreach_campaign(request.site_id)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/setup-outreach")
async def setup_outreach(request: OutreachSetupRequest, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    """
    Set up outreach by clearing existing prospect URLs and generating new ones
    """
    try:
        control_panel = create_default_control_panel()
        result = control_panel.setup_outreach(request.site_id)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))