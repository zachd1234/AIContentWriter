import re
import time
from typing import Dict, Any, Optional, List
import os
import sys
from datetime import datetime
import importlib.util

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
        
        # Fix Python path to ensure imports work correctly
        self._fix_python_path()
        
        # Import database service
        try:
            # Try relative import first
            from ..database_service import DatabaseService
            self.db_service = DatabaseService()
            print("Imported DatabaseService using relative import")
        except (ImportError, ValueError):
            try:
                # Try absolute import
                from src.database_service import DatabaseService
                self.db_service = DatabaseService()
                print("Imported DatabaseService using absolute import")
            except ImportError:
                try:
                    # Try direct import (if in same directory)
                    from database_service import DatabaseService
                    self.db_service = DatabaseService()
                    print("Imported DatabaseService using direct import")
                except ImportError:
                    print("ERROR: Could not import DatabaseService")
                    self.db_service = None
    
    def _fix_python_path(self):
        """Add necessary directories to Python path"""
        # Get the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add the project root to the path (assuming standard structure)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            print(f"Added {project_root} to Python path")
        
        # Add the src directory to the path
        src_dir = os.path.join(project_root, 'src')
        if os.path.exists(src_dir) and src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            print(f"Added {src_dir} to Python path")
    
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
            status=email_type
        )
        
        return {
            "success": True,
            "message": f"Email processed and classified as {email_type}",
            "original_email_id": original_email['email_id'],
            "classification": email_type
        }
    
    def _classify_email(self, body: str, subject: str) -> str:
        """
        Classify the email as either a bounced or a replied using rule-based detection
        and Google Gemini as a backup
        
        Args:
            body: Email body text
            subject: Email subject
            
        Returns:
            Classification string: "bounced" or "replied"
        """
        try:
            print(f"Starting email classification for subject: {subject}")
            
            # Check for common bounce patterns first (rule-based approach)
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
                "550 5.0.0",
                "address not found",
                "user unknown",
                "recipient rejected",
                "mailbox unavailable"
            ]
            
            # Check subject and body for bounce indicators
            check_text = (subject + " " + body[:500]).lower()
            for indicator in bounce_indicators:
                if indicator in check_text:
                    print(f"Bounce indicator found: {indicator}")
                    return "bounced"
            
            # If no clear bounce indicators, try using Google Gemini
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                try:
                    print("Using Google Gemini for classification")
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
                    
                    # List available models to help with debugging
                    try:
                        models = genai.list_models()
                        model_names = [model.name for model in models]
                        print(f"Available models: {model_names}")
                    except Exception as e:
                        print(f"Error listing models: {str(e)}")
                    
                    # Use gemini-pro instead of gemini-1.0-pro
                    model = genai.GenerativeModel(
                        model_name="gemini-pro",  # Updated model name
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    
                    prompt = f"""
                    Analyze this email and determine if it's a bounce notification or a human reply.
                    A bounce notification is an automated message indicating the email couldn't be delivered.
                    
                    Subject: {subject}
                    
                    Body:
                    {body[:1000]}
                    
                    Output only one word: either "bounced" or "replied"
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # Extract the classification from the response
                    classification_text = response.text.strip().lower()
                    print(f"Google Gemini classification: {classification_text}")
                    
                    # Return bounce only if explicitly classified as such
                    if "bounce" in classification_text:
                        return "bounced"
                    else:
                        return "replied"
                        
                except Exception as e:
                    print(f"Error using Google Gemini: {str(e)}")
                    # Fall back to default classification
                    return "replied"
            else:
                print("Google API key not set, skipping LLM classification")
                return "replied"
            
        except Exception as e:
            print(f"Error classifying email: {str(e)}")
            # Default to "reply" if classification fails
            return "replied"

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