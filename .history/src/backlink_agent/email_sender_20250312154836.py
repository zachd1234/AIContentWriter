import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import uuid
import hashlib
import time
import sys
from pathlib import Path

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
                  html_body: Optional[str] = None,
                  site_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Send an email with the given details and track it in the database.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Plain text email body
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            html_body: Optional HTML version of the email body
            site_id: Optional site ID for tracking purposes
            
        Returns:
            Dictionary with status and message
        """
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            return {
                "success": False,
                "message": "Email credentials not configured. Set SMTP_SERVER, SMTP_PORT, EMAIL_USERNAME, and EMAIL_PASSWORD."
            }
        
        # Generate a deterministic email ID based on subject, recipient, and timestamp
        timestamp = int(time.time())
        hash_input = f"{subject}|{to_email}|{timestamp}"
        email_id = hashlib.md5(hash_input.encode()).hexdigest()
        
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
            # Record the email in database before sending (with pending status)
            from database_service import DatabaseService
            db_service = DatabaseService()
            db_service.add_email_tracking(
                email_id=email_id,
                recipient=to_email,
                subject=subject,
                status="pending",
                site_id=site_id
            )
            
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
            
            # Update status to delivered
            db_service.update_email_status(email_id, "delivered")
            db_service.close()
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "email_id": email_id  # Return the email_id for reference
            }
            
        except Exception as e:
            # Update status to bounced if sending failed
            try:
                db_service.update_email_status(email_id, "bounced", str(e))
                db_service.close()
            except:
                pass  # If we can't update the status, just continue
            
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}",
                "email_id": email_id  # Return the email_id for reference
            }

    def send_backlink_outreach_email(self, 
                                   to_email: str, 
                                   subject: str, 
                                   body: str,
                                   site_id: int = None) -> Dict[str, Any]:
        """
        Send a backlink outreach email with tracking.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body
            site_id: ID of the site this outreach is for
            
        Returns:
            Dictionary with status and message
        """
        # Skip sending if no valid email was found
        if to_email == "NO EMAIL FOUND" or not to_email:
            return {
                "success": False,
                "message": "No valid email address found",
                "email_id": None
            }
        
        # Call the regular send_email method with the site_id
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            site_id=site_id
        )

    def send_stats_report(self, 
                         to_email: str,
                         site_id: Optional[int] = None,
                         days_to_show: int = 5,
                         include_recent_emails: bool = True,
                         recent_email_limit: int = 10) -> Dict[str, Any]:
        """
        Send a daily email report with key email statistics.
        
        Args:
            to_email: Recipient email address
            site_id: Optional site ID to filter statistics by
            days_to_show: Number of recent days to display in the report
            include_recent_emails: Whether to include a table of recent emails
            recent_email_limit: Maximum number of recent emails to include
            
        Returns:
            Dictionary with status and message
        """
        # Get statistics from database - use proper import path
        # Add the parent directory to sys.path if needed
        src_dir = Path(__file__).resolve().parent.parent
        if str(src_dir) not in sys.path:
            sys.path.append(str(src_dir))
        
        from database_service import DatabaseService
        db_service = DatabaseService()
        stats_data = db_service.get_email_stats(site_id=site_id, days=days_to_show)
        
        # Get recent emails if requested
        recent_emails = []
        if include_recent_emails:
            recent_emails = db_service.get_recent_emails(site_id=site_id, limit=recent_email_limit)
        
        db_service.close()
        
        # Set subject line
        if site_id:
            subject = f"Email Campaign Stats for Site #{site_id} - {datetime.now().strftime('%Y-%m-%d')}"
        else:
            subject = f"Email Campaign Stats Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Extract data
        daily_stats = stats_data['daily_stats']
        total_sent = stats_data['total_sent']
        total_delivered = stats_data['total_delivered']
        total_replied = stats_data['total_replied']
        total_bounced = stats_data['total_bounced']
        reply_rate = stats_data['reply_rate']
        bounce_rate = stats_data['bounce_rate']
        
        # Create plain text email body
        body = f"""Email Campaign Statistics Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
---------
Total Emails Sent: {total_sent}
Total Emails Delivered: {total_delivered}
Total Replies Received: {total_replied}
Total Bounced Emails: {total_bounced}
Cumulative Reply Rate: {reply_rate:.2f}%
Bounce Rate: {bounce_rate:.2f}%

DAILY BREAKDOWN (Last {len(daily_stats)} days):
-----------------
"""
        
        # Add daily stats
        for day in daily_stats:
            date_str = day['date']
            sent = day['sent']
            delivered = day['delivered']
            replied = day['replied']
            bounced = day['bounced']
            daily_reply_rate = day['reply_rate']
            daily_bounce_rate = day['bounce_rate']
            
            body += f"""
Date: {date_str}
  Sent: {sent}
  Delivered: {delivered}
  Replied: {replied}
  Bounced: {bounced}
  Reply Rate: {daily_reply_rate:.2f}%
  Bounce Rate: {daily_bounce_rate:.2f}%
"""
        
        # Add recent emails if available
        if recent_emails:
            body += f"""
RECENT EMAILS (Last {len(recent_emails)}):
-----------------
"""
            for email in recent_emails:
                recipient = email['recipient']
                subject = email['subject']
                status = email['status']
                sent_at = email['sent_at']
                
                body += f"""
Email ID: {email['email_id']}
  Recipient: {recipient}
  Subject: {subject}
  Status: {status}
  Sent At: {sent_at}
"""
                if email.get('reply_received_at'):
                    body += f"  Reply Received At: {email['reply_received_at']}\n"
                if email.get('bounce_reason'):
                    body += f"  Bounce Reason: {email['bounce_reason']}\n"
        
        # Create HTML version
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; font-size: 24px; margin-bottom: 20px; }}
                h2 {{ color: #3498db; font-size: 20px; margin-top: 30px; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .summary p {{ margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #3498db; color: white; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .highlight {{ font-weight: bold; color: #2980b9; }}
                .warning {{ font-weight: bold; color: #e74c3c; }}
                .status-delivered {{ color: #27ae60; }}
                .status-replied {{ color: #2980b9; font-weight: bold; }}
                .status-bounced {{ color: #e74c3c; }}
                .status-pending {{ color: #f39c12; }}
                .email-table {{ font-size: 14px; }}
                .email-table th {{ font-size: 13px; }}
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
                    <p><strong>Total Replies Received:</strong> <span class="highlight">{total_replied}</span></p>
                    <p><strong>Total Bounced Emails:</strong> <span class="warning">{total_bounced}</span></p>
                    <p><strong>Cumulative Reply Rate:</strong> <span class="highlight">{reply_rate:.2f}%</span></p>
                    <p><strong>Bounce Rate:</strong> <span class="warning">{bounce_rate:.2f}%</span></p>
                </div>
                
                <h2>Daily Breakdown (Last {len(daily_stats)} days)</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Sent</th>
                        <th>Delivered</th>
                        <th>Replied</th>
                        <th>Bounced</th>
                        <th>Reply Rate</th>
                        <th>Bounce Rate</th>
                    </tr>
        """
        
        # Add rows for each day
        for day in daily_stats:
            date_str = day['date']
            sent = day['sent']
            delivered = day['delivered']
            replied = day['replied']
            bounced = day['bounced']
            daily_reply_rate = day['reply_rate']
            daily_bounce_rate = day['bounce_rate']
            
            html_body += f"""
                    <tr>
                        <td>{date_str}</td>
                        <td>{sent}</td>
                        <td>{delivered}</td>
                        <td>{replied}</td>
                        <td>{bounced}</td>
                        <td>{daily_reply_rate:.2f}%</td>
                        <td>{daily_bounce_rate:.2f}%</td>
                    </tr>
            """
        
        # Close the daily stats table
        html_body += """
                </table>
        """
        
        # Add recent emails table if available
        if recent_emails:
            html_body += f"""
                <h2>Recent Emails (Last {len(recent_emails)})</h2>
                <table class="email-table">
                    <tr>
                        <th>Recipient</th>
                        <th>Subject</th>
                        <th>Status</th>
                        <th>Sent At</th>
                        <th>Reply/Bounce</th>
                    </tr>
        """
            
            for email in recent_emails:
                recipient = email['recipient']
                # Truncate subject if too long
                subject = email['subject']
                if len(subject) > 40:
                    subject = subject[:37] + "..."
                
                status = email['status']
                sent_at = email['sent_at']
                
                # Determine status class for styling
                status_class = ""
                if status == "delivered":
                    status_class = "status-delivered"
                elif status == "replied":
                    status_class = "status-replied"
                elif status == "bounced":
                    status_class = "status-bounced"
                elif status == "pending":
                    status_class = "status-pending"
                
                # Determine additional info (reply or bounce)
                additional_info = ""
                if email.get('reply_received_at'):
                    additional_info = f"Replied: {email['reply_received_at']}"
                elif email.get('bounce_reason'):
                    bounce_reason = email['bounce_reason']
                    if len(bounce_reason) > 40:
                        bounce_reason = bounce_reason[:37] + "..."
                    additional_info = f"Reason: {bounce_reason}"
                
                html_body += f"""
                    <tr>
                        <td>{recipient}</td>
                        <td>{subject}</td>
                        <td class="{status_class}">{status}</td>
                        <td>{sent_at}</td>
                        <td>{additional_info}</td>
                    </tr>
                """
            
            # Close the recent emails table
            html_body += """
                </table>
            """
        
        # Close the HTML
        html_body += """
            </div>
        </body>
        </html>
        """
        
        # Send the email with both plain text and HTML versions
        return self.send_email(
            to_email=to_email,
            subject="Backlink Email Report",
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
        
        # Send the stats report
        result = sender.send_stats_report(to_email=to_email)
    
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