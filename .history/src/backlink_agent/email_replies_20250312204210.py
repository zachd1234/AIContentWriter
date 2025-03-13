import re
import time
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

# Import Google Gemini for classification
import google.generativeai as genai


class EmailReplyProcessor:
    def __init__(self):
        """Initialize the email reply processor"""
        # Set up Google Gemini client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY environment variable not set")
        else:
            genai.configure(api_key=api_key)
        
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
        Use Google Gemini to classify the email as a bounce, reply, or other type
        
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
            
            # Use rule-based classification for common patterns
            lower_subject = subject.lower()
            lower_body = body.lower()
            
            # Check for obvious rejections
            rejection_phrases = [
                "not interested",
                "no thank you",
                "no thanks",
                "please remove",
                "unsubscribe",
                "stop contacting",
                "do not contact"
            ]
            
            for phrase in rejection_phrases:
                if phrase in lower_subject or phrase in lower_body[:300]:
                    return "not_interested"
            
            # Check for obvious interest
            interest_phrases = [
                "sounds good",
                "interested",
                "tell me more",
                "would like to",
                "sounds interesting",
                "let's discuss",
                "let's talk",
                "please send more"
            ]
            
            for phrase in interest_phrases:
                if phrase in lower_subject or phrase in lower_body[:300]:
                    return "interested"
            
            # Use Google Gemini for more complex classification
            try:
                # Configure the model
                generation_config = {
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 50,
                }
                
                safety_settings = [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                ]
                
                # Initialize the model
                model = genai.GenerativeModel(
                    model_name="gemini-1.0-pro",
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
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
                
                response = model.generate_content(prompt)
                
                # Extract the classification from the response
                classification_text = response.text.strip().lower()
                
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
                print(f"Error using Google Gemini: {str(e)}")
                # Fall back to rule-based classification
                return "reply"
                
        except Exception as e:
            print(f"Error classifying email: {str(e)}")
            # Default to "reply" if classification fails
            return "reply"

def main():
    """
    Test function for the EmailReplyProcessor
    """
    print("Starting EmailReplyProcessor test...")
    
    # Create an instance of the processor
    print("Initializing EmailReplyProcessor...")
    processor = EmailReplyProcessor()
    print("EmailReplyProcessor initialized successfully")
    
    # Test email data
    print("\nPreparing test email data...")
    test_email = {
        "sender": "info@fit360fl.com",
        "recipient": "ruckquest@gmail.com",
        "subject": "Re: Your outreach about fitness collaboration",
        "body_plain": """
        Hi there,
        
        Thanks for reaching out about the potential collaboration. I'd be interested in learning more about what you have in mind.
        
        Could you provide some more details about your proposal and what kind of content you're looking for?
        
        Best regards,
        John Smith
        Fitness Director
        Fit360 Florida
        www.fit360fl.com
        """,
        "body_html": "<html><body><p>Hi there,</p><p>Thanks for reaching out about the potential collaboration. I'd be interested in learning more about what you have in mind.</p><p>Could you provide some more details about your proposal and what kind of content you're looking for?</p><p>Best regards,<br>John Smith<br>Fitness Director<br>Fit360 Florida<br>www.fit360fl.com</p></body></html>",
        "timestamp": "2025-03-13T10:45:22Z",
        "message_id": "message123456@mail.gmail.com"
    }
    print(f"Test email prepared from: {test_email['sender']}")
    print(f"Subject: {test_email['subject']}")
    print(f"First 100 chars of body: {test_email['body_plain'][:100].strip()}")
    
    # Process the test email
    print("\nProcessing test email...")
    try:
        result = processor.process_incoming_email(
            sender=test_email["sender"],
            recipient=test_email["recipient"],
            subject=test_email["subject"],
            body_plain=test_email["body_plain"],
            body_html=test_email["body_html"],
            timestamp=test_email["timestamp"],
            message_id=test_email["message_id"]
        )
        print("Email processing completed successfully")
    except Exception as e:
        print(f"ERROR processing email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return
    
    # Print the result
    print("\nProcessing Result:")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    if result['success']:
        print(f"Original Email ID: {result.get('original_email_id', 'N/A')}")
        print(f"Classification: {result.get('classification', 'N/A')}")
    else:
        print("Processing failed. Check database connection and data.")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 