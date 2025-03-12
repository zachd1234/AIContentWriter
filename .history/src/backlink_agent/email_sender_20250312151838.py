import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

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

    def send_stats_report(self, 
                         to_email: str,
                         stats_data: Dict[str, Any],
                         days_to_show: int = 5) -> Dict[str, Any]:
        """
        Send a daily email report with key email statistics.
        
        Args:
            to_email: Recipient email address
            stats_data: Dictionary containing the statistics data with keys:
                - daily_stats: List of dicts with date, sent, delivered, replied for each day
                - total_sent: Total emails sent all-time
                - total_delivered: Total emails delivered all-time
                - total_replied: Total emails that received replies
                - cumulative_reply_rate: Overall reply rate percentage
            days_to_show: Number of recent days to display in the report
            
        Returns:
            Dictionary with status and message
        """
        subject = f"Email Campaign Stats Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Ensure we have the required data
        if not stats_data or not all(key in stats_data for key in 
                                    ['daily_stats', 'total_sent', 'total_delivered', 
                                     'total_replied', 'cumulative_reply_rate']):
            return {
                "success": False,
                "message": "Incomplete statistics data provided"
            }
        
        # Extract data
        daily_stats = stats_data['daily_stats'][-days_to_show:] if stats_data['daily_stats'] else []
        total_sent = stats_data['total_sent']
        total_delivered = stats_data['total_delivered']
        total_replied = stats_data['total_replied']
        reply_rate = stats_data['cumulative_reply_rate']
        
        # Create plain text email body
        body = f"""Email Campaign Statistics Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
---------
Total Emails Sent: {total_sent}
Total Emails Delivered: {total_delivered}
Total Replies Received: {total_replied}
Cumulative Reply Rate: {reply_rate:.2f}%

DAILY BREAKDOWN (Last {len(daily_stats)} days):
-----------------
"""
        
        # Add daily stats
        for day in daily_stats:
            date_str = day['date']
            sent = day['sent']
            delivered = day['delivered']
            replied = day['replied']
            daily_rate = (replied / delivered * 100) if delivered > 0 else 0
            
            body += f"""
Date: {date_str}
  Sent: {sent}
  Delivered: {delivered}
  Replied: {replied}
  Reply Rate: {daily_rate:.2f}%
"""
        
        # Create HTML version
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; font-size: 24px; margin-bottom: 20px; }}
                h2 {{ color: #3498db; font-size: 20px; margin-top: 30px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .summary p {{ margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #3498db; color: white; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .highlight {{ font-weight: bold; color: #2980b9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Email Campaign Statistics Report</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="summary">
                    <h2>Summary</h2>
                    <p><strong>Total Emails Sent:</strong> {total_sent}</p>
                    <p><strong>Total Emails Delivered:</strong> {total_delivered}</p>
                    <p><strong>Total Replies Received:</strong> {total_replied}</p>
                    <p><strong>Cumulative Reply Rate:</strong> <span class="highlight">{reply_rate:.2f}%</span></p>
                </div>
                
                <h2>Daily Breakdown (Last {len(daily_stats)} days)</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Sent</th>
                        <th>Delivered</th>
                        <th>Replied</th>
                        <th>Reply Rate</th>
                    </tr>
        """
        
        # Add rows for each day
        for day in daily_stats:
            date_str = day['date']
            sent = day['sent']
            delivered = day['delivered']
            replied = day['replied']
            daily_rate = (replied / delivered * 100) if delivered > 0 else 0
            
            html_body += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{sent}</td>
                        <td>{delivered}</td>
                        <td>{replied}</td>
                        <td>{daily_rate:.2f}%</td>
                    </tr>
            """
        
        # Close the HTML
        html_body += """
                </table>
            </div>
        </body>
        </html>
        """
        
        # Send the email with both plain text and HTML versions
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body
        )

def main():
    """Example usage of the EmailSender."""
    # Create an instance of EmailSender
    sender = EmailSender()
    
    print("Choose an option:")
    print("1. Send a test email")
    print("2. Send a test stats report")
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        # Example email
        to_email = input("Enter recipient email: ")
        subject = "Test Email from Backlink Agent"
        body = "This is a test email sent from the Backlink Agent application."
        
        # Send the email
        result = sender.send_email(to_email=to_email, subject=subject, body=body)
    
    elif choice == "2":
        # Example stats report
        to_email = input("Enter recipient email: ")
        
        # Create sample stats data
        from datetime import datetime, timedelta
        
        stats_data = {
            'daily_stats': [
                {
                    'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'),
                    'sent': 120,
                    'delivered': 115,
                    'replied': 12
                },
                {
                    'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                    'sent': 85,
                    'delivered': 82,
                    'replied': 9
                },
                {
                    'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                    'sent': 95,
                    'delivered': 92,
                    'replied': 11
                },
                {
                    'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    'sent': 110,
                    'delivered': 108,
                    'replied': 15
                },
                {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'sent': 100,
                    'delivered': 98,
                    'replied': 13
                }
            ],
            'total_sent': 2500,
            'total_delivered': 2420,
            'total_replied': 290,
            'cumulative_reply_rate': (290 / 2420) * 100  # About 11.98%
        }
        
        # Send the stats report
        result = sender.send_stats_report(to_email=to_email, stats_data=stats_data)
    
    else:
        print("Invalid choice.")
        return
    
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