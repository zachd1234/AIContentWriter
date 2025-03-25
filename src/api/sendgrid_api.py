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
    """
    Main function to test SendGrid API
    """
    print("SendGrid API Test")
    print("-----------------")
    
    print("Choose an option:")
    print("1. Send a basic test email")
    print("2. Send an email with CC and BCC")
    print("3. Test line break handling")
    choice = input("Enter your choice (1, 2, or 3): ")
    
    if choice == "3":
        # Test case specifically for line break issues
        to_email = "ruckquest@gmail.com"
        subject = "Line Break Test Email"
        
        # Create a test message with intentional line breaks
        test_content = """Hey, Golden Endurance Team,

I loved your article about running with illness! Very interesting how you challenge the unvalidated opinions in medical pamphlets with a focus on personal experience and research.

Golden Endurance is all about peak performance, and while you cover many aspects of endurance, building a robust strength foundation is often the missing link.

Rucking is a low-impact yet highly effective way to forge that exact kind of strength-based endurance, something your audience could greatly benefit from incorporating into their training.

I'm Liam Thompson, founder of Ruck Quest, and we'd love to contribute an educational guest post that explores how rucking can enhance overall endurance for your readers.

Would you be open to seeing some topic ideas?

Best,
Liam Thompson

P.S. Here's a sample of a recent post we wrote about affordable rucking backpacks: https://ruckquest.com/top-5-affordable-rucking-backpacks/"""
        
        print("\n--- Original Content with Line Breaks ---")
        print(test_content)
        print("\n--- End of Original Content ---\n")
        
        # Test different approaches
        print("Testing different approaches to preserve line breaks...")
        
        # Approach 1: Plain text only
        print("\nApproach 1: Plain text only")
        result1 = send_email(
            to_email=to_email,
            subject=subject + " (Plain Text Only)",
            html_content="",  # Empty HTML content
            plain_content=test_content
        )
        print(f"Result: {'Success' if result1['success'] else 'Failed'}")
        
        # Approach 2: HTML with <br> tags
        html_with_br = test_content.replace('\n', '<br>\n')
        print("\nApproach 2: HTML with <br> tags")
        print("HTML content being sent:")
        print(html_with_br[:100] + "...")  # Print first 100 chars
        result2 = send_email(
            to_email=to_email,
            subject=subject + " (HTML with <br> tags)",
            html_content=html_with_br,
            plain_content=test_content
        )
        print(f"Result: {'Success' if result2['success'] else 'Failed'}")
        
        # Approach 3: HTML with pre-wrap style
        html_with_style = f"<div style='white-space: pre-wrap; font-family: sans-serif;'>{test_content}</div>"
        print("\nApproach 3: HTML with pre-wrap style")
        print("HTML content being sent:")
        print(html_with_style[:100] + "...")  # Print first 100 chars
        result3 = send_email(
            to_email=to_email,
            subject=subject + " (HTML with pre-wrap style)",
            html_content=html_with_style,
            plain_content=test_content
        )
        print(f"Result: {'Success' if result3['success'] else 'Failed'}")
        
        # Approach 4: HTML with paragraphs
        paragraphs = test_content.split('\n\n')
        html_with_paragraphs = ''.join([f"<p>{p.replace('\n', '<br>')}</p>" for p in paragraphs])
        print("\nApproach 4: HTML with paragraphs")
        print("HTML content being sent:")
        print(html_with_paragraphs[:100] + "...")  # Print first 100 chars
        result4 = send_email(
            to_email=to_email,
            subject=subject + " (HTML with paragraphs)",
            html_content=html_with_paragraphs,
            plain_content=test_content
        )
        print(f"Result: {'Success' if result4['success'] else 'Failed'}")
        
        print("\nAll test emails sent. Please check zachderhake@gmail.com to see which approach worked best.")
        return
    
    # Original code for options 1 and 2
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