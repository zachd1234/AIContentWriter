# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
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
        
        # Add BCC recipients if provided
        if bcc_emails:
            for bcc_email in bcc_emails:
                message.add_bcc(Bcc(bcc_email))
        
        # Initialize SendGrid client
        sg = SendGridAPIClient(api_key)
        
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
        traceback.print_exc()
        
        return {
            "success": False,
            "message": f"Failed to send email: {error_message}"
        }

def main():
    """
    Main function to test SendGrid API
    """
    print("SendGrid API Test")
    print("-----------------")
    
    print("Choose an option:")
    print("1. Send a basic test email")
    print("2. Send an email with CC and BCC")
    choice = input("Enter your choice (1 or 2): ")
    
    # Get common email details from user input
    to_email = input("Enter recipient email: ")
    subject = input("Enter email subject: ") or "Test Email from SendGrid API"
    html_content = input("Enter HTML content (or press Enter for default): ") or "<strong>This is a test email sent using SendGrid's API</strong>"
    plain_content = input("Enter plain text content (or press Enter for default): ") or "This is a test email sent using SendGrid's API"
    
    if choice == "2":
        # Get CC and BCC recipients
        cc_input = input("Enter CC recipients (comma-separated, or press Enter for none): ")
        cc_emails = [email.strip() for email in cc_input.split(",")] if cc_input else None
        
        bcc_input = input("Enter BCC recipients (comma-separated, or press Enter for none): ")
        bcc_emails = [email.strip() for email in bcc_input.split(",")] if bcc_input else None
        
        # Send email with CC and BCC
        result = send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails
        )
    else:
        # Send basic email
        result = send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content
        )
    
    # Print the result
    if result["success"]:
        print("\nEmail sent successfully!")
        print(f"Status code: {result.get('status_code')}")
    else:
        print("\nFailed to send email.")
        print(f"Error: {result['message']}")
        print("\nCommon issues:")
        print("1. Sender email address not verified in your SendGrid account")
        print("2. API key doesn't have permission to send emails")
        print("3. Free SendGrid account limitations")
        print("\nTroubleshooting steps:")
        print("- Verify your sender email in the SendGrid dashboard")
        print("- Check API key permissions")
        print("- Try sending a test email from the SendGrid dashboard")
        print("- Ensure your SendGrid account is fully set up and not in sandbox mode")

if __name__ == "__main__":
    main()