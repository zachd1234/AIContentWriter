# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

def send_test_email(from_email, to_email, subject, content):
    """
    Send a test email using SendGrid API
    
    Args:
        from_email: Sender email address
        to_email: Recipient email address
        subject: Email subject line
        content: HTML content of the email
        
    Returns:
        Response from SendGrid API
    """
    print(f"Sending test email via SendGrid from {from_email} to {to_email}")
    print(f"Subject: {subject}")
    
    # Check if API key is available
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("Error: SENDGRID_API_KEY environment variable not set")
        return None
    
    print(f"API Key (first 5 chars): {api_key[:5]}...")
    
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=content)
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"Response status code: {response.status_code}")
        print(f"Response body: {response.body}")
        print(f"Response headers: {response.headers}")
        return response
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """
    Main function to test SendGrid API
    """
    print("SendGrid API Test")
    print("-----------------")
    
    # Get email details from user input
    from_email = input("Enter sender email: ")
    to_email = input("Enter recipient email: ")
    subject = input("Enter email subject: ") or "Test Email from SendGrid API"
    content = input("Enter HTML content (or press Enter for default): ") or "<strong>This is a test email sent using SendGrid's API</strong>"
    
    # Send the test email
    response = send_test_email(from_email, to_email, subject, content)
    
    if response and response.status_code >= 200 and response.status_code < 300:
        print("\nEmail sent successfully!")
    else:
        print("\nFailed to send email.")
        print("\nCommon issues:")
        print("1. Sender email address not verified in your SendGrid account")
        print("2. API key doesn't have permission to send emails")
        print("3. Free SendGrid account limitations")
        print("\nTroubleshooting steps:")
        print("- Verify your sender email in the SendGrid dashboard")
        print("- Check API key permissions")
        print("- Try sending a test email from the SendGrid dashboard")

if __name__ == "__main__":
    main()