from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
import asyncio
from src.api_handler import ContentAPIHandler
import os
from src.backlink_agent.control_panel import create_default_control_panel
import json
from typing import Optional, Dict, Any
from src.backlink_agent.email_replies import EmailReplyProcessor
import aiohttp
import requests
import time

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

# Define the model for incoming email data
class EmailWebhookRequest(BaseModel):
    sender: str
    recipient: str
    subject: str
    body_plain: str
    body_html: Optional[str] = None
    timestamp: Optional[str] = None
    message_id: Optional[str] = None

async def ping_post_pitch_service():
    """Ping the post-pitch service to initiate wake-up from cold start"""
    url = "https://post-pitch-fork.onrender.com"
    try:
        # Create a background task to ping the service
        async with aiohttp.ClientSession() as session:
            print(f"Pinging post-pitch service to initiate wake-up...")
            asyncio.create_task(session.get(url, timeout=30))
            print(f"Wake-up request sent to post-pitch service")
    except Exception as e:
        print(f"Error initiating post-pitch service wake-up: {str(e)}")

@app.post("/generate")
async def generate_post(keyword: str, base_url: str, site_id: int, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    """
    Generate a complete blog post with media and internal links, then run outreach campaign
    """
    try:
        # Ping the post-pitch service to start waking it up
        await ping_post_pitch_service()
        
        # Generate the post
        handler = ContentAPIHandler()
        result = await handler.generate_complete_post(keyword, base_url)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate content")
        
        # Create control panel
        control_panel = create_default_control_panel()
        
        # Send daily stats report
        try:
            stats_result = control_panel.send_daily_stats_report()
            print(f"Stats report sent: {stats_result['message']}")
        except Exception as e:
            print(f"Error sending stats report: {str(e)}")
        
        # Check if outreach list exists and run outreach campaign if it does
        try:
            # Check if outreach list is empty before running campaign
            if control_panel.has_outreach_prospects(site_id):
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
            else:
                # Skip outreach if no prospects exist
                return {
                    "status": "success",
                    "data": result,
                    "outreach": {
                        "status": "skipped",
                        "message": "No outreach prospects found for this site"
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
        print("Stats report")
        stats_result = control_panel.send_daily_stats_report()
        print(f"Stats report sent: {stats_result['message']}")
    except Exception as e:
            print(f"Error sending stats report: {str(e)}")

    try:
        control_panel = create_default_control_panel()
        result = control_panel.run_outreach_campaign(request.site_id)
        
        return {
            "status": "success",
            "data": "Outreach campaign run"
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

@app.post("/email-webhook")
async def email_webhook(request: EmailWebhookRequest, x_api_key: str = Header(None)):
    """
    Webhook endpoint to receive incoming emails from Zapier
    """
    # Optional: Verify API key if you set one in Zapier
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        print(f"Received email from {request.sender} to {request.recipient}")
        print(f"Subject: {request.subject}")
        print(f"Body: {len(request.body_plain)}")
        
        # Initialize the email processor
        processor = EmailReplyProcessor()
        
        # Process the incoming email
        result = processor.process_incoming_email(
            sender=request.sender,
            recipient=request.recipient,
            subject=request.subject,
            body_plain=request.body_plain,
            body_html=request.body_html,
            timestamp=request.timestamp,
            message_id=request.message_id
        )
        
        print(f"Email processing result: {result}")
        
        return {"status": "success", "message": "Email processed successfully", "result": result}
        
    except Exception as e:
        print(f"Error processing email webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/test-connection")
async def test_connection():
    """Test connection to the post-pitch service"""
    url = "https://post-pitch-fork.onrender.com/"
    
    try:
        # Test basic connectivity
        start_time = time.time()
        response = requests.get(url, timeout=10)
        elapsed_time = time.time() - start_time
        
        return {
            "success": True,
            "elapsed_time": f"{elapsed_time:.2f} seconds",
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body_preview": response.text[:200]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }