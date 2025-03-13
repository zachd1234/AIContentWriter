import re
import time
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

# Import OpenAI for classification
import openai

class EmailReplyProcessor:
    def __init__(self):
        """Initialize the email reply processor"""
        # Set up OpenAI client
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Try to import database service
        try:
            from src.database_service import DatabaseService
            self.db_service = DatabaseService()
        except ImportError:
            print("Warning: DatabaseService not available")
            self.db_service = None
    
    def process_incoming_email(self, 
                              sender: str, 
                              recipient: str, 
                              subject: str, 
                              body_plain: str,
                              body_html: Optional[str] = None,
                              timestamp: Optional[str] = None,
                              message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an incoming email and determine if it's a reply to one of our outreach emails
        
        Args:
            sender: Email address of the sender
            recipient: Email address of the recipient
            subject: Email subject line
            body_plain: Plain text email body
            body_html: Optional HTML version of the email body
            timestamp: Optional timestamp of when the email was received
            message_id: Optional message ID
            
        Returns:
            Dictionary with processing results
        """
        print(f"Processing email from {sender} to {recipient}")
        print(f"Subject: {subject}")
        
        if not self.db_service:
            return {
                "success": False,
                "message": "Database service not available"
            }
        
        # Step 1: Find the most recent email we sent to this sender
        # (The sender of this email was the recipient of our outreach email)
        original_emails = self.db_service.find_recent_emails_by_recipient(sender)
        
        if not original_emails:
            return {
                "success": False,
                "message": f"No outreach emails found sent to {sender}"
            }
        
        # Get the most recent email we sent to this person
        original_email = original_emails[0]  # Most recent first
        print(f"Found original email with ID: {original_email['email_id']}")
        
        # Step 2: Classify the reply using AI
        email_type = self._classify_email(body_plain, subject)
        print(f"Email classified as: {email_type}")
        
        # Step 3: Update the status in the database
        self.db_service.update_email_status(
            email_id=original_email['email_id'],
            status=email_type,
            response_text=body_plain[:500]  # Store first 500 chars of the response
        )
        
        return {
            "success": True,
            "message": f"Email processed and classified as {email_type}",
            "original_email_id": original_email['email_id'],
            "classification": email_type
        }
    
    def _classify_email(self, body: str, subject: str) -> str:
        """
        Use AI to classify the email as a bounce, reply, or other type
        
        Args:
            body: Email body text
            subject: Email subject
            
        Returns:
            Classification string: "bounce", "reply", "interested", "not_interested", or "other"
        """
        try:
            # Check for common bounce patterns first (no need to use AI for these)
            bounce_indicators = [
                "mailer-daemon",
                "mail delivery failed",
                "undeliverable",
                "delivery status notification",
                "delivery failure",
                "failed delivery",
                "not delivered",
                "delivery has failed",
                "550 5.1.1",
                "550 5.0.0"
            ]
            
            # Check subject and first 200 chars of body for bounce indicators
            check_text = (subject + " " + body[:200]).lower()
            for indicator in bounce_indicators:
                if indicator in check_text:
                    return "bounce"
            
            # Use AI to classify more complex responses
            prompt = f"""
            Analyze this email reply and classify it into one of these categories:
            - bounce: An automated message indicating the email couldn't be delivered
            - reply: A neutral or unclear response that needs human review
            - interested: A positive response showing interest in our outreach
            - not_interested: A clear rejection or lack of interest
            - other: Something else entirely
            
            Subject: {subject}
            
            Body:
            {body[:1000]}
            
            Classification:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an email classification assistant. Classify the email reply into one of these categories: bounce, reply, interested, not_interested, or other."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0
            )
            
            # Extract the classification from the response
            classification_text = response.choices[0].message.content.strip().lower()
            
            # Map to our standard categories
            if "bounce" in classification_text:
                return "bounce"
            elif "interested" in classification_text:
                return "interested"
            elif "not_interested" in classification_text:
                return "not_interested"
            elif "reply" in classification_text:
                return "reply"
            else:
                return "other"
                
        except Exception as e:
            print(f"Error classifying email: {str(e)}")
            # Default to "reply" if classification fails
            return "reply" 