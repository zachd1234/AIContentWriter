import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any

class EmailSender:
    def __init__(self, 
                 smtp_server: str = None,
                 smtp_port: int = None,
                 username: str = None, 
                 password: str = None):
        """
        Initialize the EmailSender with SMTP server details.
        
        Args:
            smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
            smtp_port: SMTP server port (e.g., 587 for TLS)
            username: Email username/address
            password: Email password or app password
        """
        # Use provided values or fall back to environment variables
        self.smtp_server = smtp_server or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", 587))
        self.username = username or os.environ.get("EMAIL_USERNAME")
        self.password = password or os.environ.get("EMAIL_PASSWORD")
        
        # Validate that we have the necessary credentials
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            print("Warning: Email credentials not fully configured. Email sending may fail.")
    
    def send_email(self, 
                  to_email: str, 
                  subject: str, 
                  body: str,
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None,
                  html_body: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an email with the given details.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Plain text email body
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            html_body: Optional HTML version of the email body
            
        Returns:
            Dictionary with status and message
        """
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            return {
                "success": False,
                "message": "Email credentials not configured. Set SMTP_SERVER, SMTP_PORT, EMAIL_USERNAME, and EMAIL_PASSWORD."
            }
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC recipients if provided
        if cc:
            msg['Cc'] = ", ".join(cc)
            
        # Add plain text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.ehlo()  # Identify to the SMTP server
            server.starttls()  # Secure the connection
            server.ehlo()  # Re-identify over TLS connection
            
            # Login to the server
            server.login(self.username, self.password)
            
            # Determine all recipients
            all_recipients = [to_email]
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Send email
            server.sendmail(self.username, all_recipients, msg.as_string())
            
            # Close connection
            server.quit()
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }

    def send_backlink_outreach_email(self,
                                     to_email: str,
                                     website_name: str,
                                     blog_title: str,
                                     personalized_note: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a backlink outreach email to a prospect.
        
        Args:
            to_email: Recipient email address
            website_name: Name of the recipient's website
            blog_title: Title of your blog post
            personalized_note: Optional personalized message
            
        Returns:
            Dictionary with status and message
        """
        subject = f"Collaboration opportunity with {website_name}"
        
        # Create email body
        body = f"""Hello {website_name} team,

I recently came across your website and really enjoyed your content. I'm reaching out because I've written an article titled "{blog_title}" that I believe would be valuable to your audience.

"""
        
        # Add personalized note if provided
        if personalized_note:
            body += f"{personalized_note}\n\n"
            
        body += """I'd be happy to discuss ways we could collaborate, such as:
- Guest posting on your site
- Including a link to my article in your resources
- Cross-promotion opportunities

Would you be interested in exploring this further? I'm open to any ideas you might have.

Looking forward to your response!

Best regards,
"""
        
        # Send the email
        return self.send_email(to_email=to_email, subject=subject, body=body)


def main():
    """Example usage of the EmailSender."""
    # Create an instance of EmailSender
    sender = EmailSender()
    
    # Example email
    to_email = input("Enter recipient email: ")
    subject = "Test Email from Backlink Agent"
    body = "This is a test email sent from the Backlink Agent application."
    
    # Send the email
    result = sender.send_email(to_email=to_email, subject=subject, body=body)
    
    # Print the result
    if result["success"]:
        print(f"Success: {result['message']}")
    else:
        print(f"Error: {result['message']}")
        print("\nTo use this module, you need to set the following environment variables:")
        print("  - SMTP_SERVER (e.g., smtp.gmail.com)")
        print("  - SMTP_PORT (e.g., 587)")
        print("  - EMAIL_USERNAME (your email address)")
        print("  - EMAIL_PASSWORD (your email password or app password)")
        print("\nFor Gmail, you'll need to use an App Password instead of your regular password.")
        print("Learn more: https://support.google.com/accounts/answer/185833")

if __name__ == "__main__":
    main() 