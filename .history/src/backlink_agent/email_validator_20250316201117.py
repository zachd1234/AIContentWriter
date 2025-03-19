import re
import dns.resolver
import smtplib
from typing import Tuple, List, Set, Dict, Any, Optional

# List of known disposable email domains
DISPOSABLE_DOMAINS: Set[str] = {
    "mailinator.com", "tempmail.com", "guerrillamail.com",
    "10minutemail.com", "yopmail.com", "throwawaymail.com",
    "temp-mail.org", "fakeinbox.com", "sharklasers.com",
    "armyspy.com", "cuvox.de", "dayrep.com",
    "einrot.com", "fleckens.hu", "gustr.com",
    "jourrapide.com", "rhyta.com", "superrito.com",
    "teleworm.us", "trashmail.com", "mailnesia.com",
    "mailcatch.com", "dispostable.com", "maildrop.cc",
    "harakirimail.com", "getairmail.com", "getnada.com",
    "inboxalias.com", "tempr.email", "spamgourmet.com",
    "mytemp.email", "burnermail.io", "temp-mail.io",
    "emailondeck.com", "mohmal.com", "incognitomail.com",
    "tempmailaddress.com", "tempail.com", "throwawaymail.com",
    "wegwerfemail.de", "trashmail.de", "emailsensei.com"
}

class EmailValidator:
    def __init__(self, 
                 sender_email: str = "verification@example.com",
                 timeout: int = 10,
                 debug_level: int = 0):
        """
        Initialize the email validator.
        
        Args:
            sender_email: Email to use as the sender in SMTP checks
            timeout: Timeout in seconds for DNS and SMTP operations
            debug_level: Debug level for SMTP operations (0-2)
        """
        self.sender_email = sender_email
        self.timeout = timeout
        self.debug_level = debug_level
    
    def is_valid_email_format(self, email: str) -> bool:
        """
        Check if an email follows standard email formatting.
        
        Args:
            email: The email address to validate
            
        Returns:
            True if the email format is valid, False otherwise
        """
        # More comprehensive regex that handles most valid email formats
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None
    
    def get_mx_record(self, domain: str) -> Optional[str]:
        """
        Check if the domain has an MX record (Mail Exchange).
        
        Args:
            domain: The domain to check
            
        Returns:
            The MX record if found, None otherwise
        """
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout
            mx_records = resolver.resolve(domain, 'MX')
            return str(mx_records[0].exchange)
        except Exception as e:
            print(f"MX record lookup failed for {domain}: {str(e)}")
            return None
    
    def is_valid_domain(self, email: str) -> bool:
        """
        Extract domain from email and verify its MX record.
        
        Args:
            email: The email address to validate
            
        Returns:
            True if the domain has valid MX records, False otherwise
        """
        try:
            domain = email.split('@')[-1]
            return self.get_mx_record(domain) is not None
        except Exception as e:
            print(f"Domain validation failed for {email}: {str(e)}")
            return False
    
    def verify_email_smtp(self, email: str) -> Tuple[bool, str]:
        """
        Check if an email address exists using SMTP.
        
        Args:
            email: The email address to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            domain = email.split('@')[1]
            mx_record = self.get_mx_record(domain)

            if not mx_record:
                return False, "No MX record found"

            # Connect to mail server
            server = smtplib.SMTP(timeout=self.timeout)
            server.set_debuglevel(self.debug_level)
            
            # Connect to the MX server
            server.connect(mx_record)
            
            # Greet the server
            server.ehlo_or_helo_if_needed()
            
            # Some servers require STARTTLS
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
                
            # Start the email sending simulation
            server.mail(self.sender_email)
            
            # Check if recipient exists
            code, message = server.rcpt(email)
            server.quit()
            
            # 250 is the success code for SMTP
            if code == 250:
                return True, "Email address exists"
            elif code == 550:
                return False, "Email address does not exist"
            else:
                return False, f"SMTP Error: {message.decode() if isinstance(message, bytes) else message}"
        
        except smtplib.SMTPServerDisconnected:
            return False, "Server disconnected"
        except smtplib.SMTPConnectError:
            return False, "Failed to connect to server"
        except smtplib.SMTPHeloError:
            return False, "Server rejected HELO/EHLO"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed"
        except smtplib.SMTPException as e:
            return False, f"SMTP Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def is_disposable_email(self, email: str) -> bool:
        """
        Check if email is from a disposable email service.
        
        Args:
            email: The email address to check
            
        Returns:
            True if the email is from a disposable domain, False otherwise
        """
        try:
            domain = email.split('@')[1].lower()
            return domain in DISPOSABLE_DOMAINS
        except Exception:
            # If we can't parse the domain, assume it's invalid
            return True
    
    def is_valid_email(self, email: str, check_smtp: bool = False) -> Dict[str, Any]:
        """
        Run all validation steps and return the email status.
        
        Args:
            email: The email address to validate
            check_smtp: Whether to perform SMTP verification (slower but more accurate)
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "email": email,
            "is_valid": False,
            "reason": None,
            "details": {}
        }
        
        # Basic validation
        if not email or '@' not in email:
            result["reason"] = "Invalid email format: missing @ symbol"
            return result
        
        # 1. Syntax Check
        syntax_valid = self.is_valid_email_format(email)
        result["details"]["syntax_valid"] = syntax_valid
        if not syntax_valid:
            result["reason"] = "Invalid email format"
            return result
        
        # 2. Domain Check
        domain_valid = self.is_valid_domain(email)
        result["details"]["domain_valid"] = domain_valid
        if not domain_valid:
            result["reason"] = "Domain does not exist or has no mail server"
            return result
        
        # 3. Disposable Email Detection
        is_disposable = self.is_disposable_email(email)
        result["details"]["is_disposable"] = is_disposable
        if is_disposable:
            result["reason"] = "Disposable email address"
            return result
        
        # 4. SMTP Verification (optional)
        if check_smtp:
            smtp_valid, smtp_message = self.verify_email_smtp(email)
            result["details"]["smtp_valid"] = smtp_valid
            result["details"]["smtp_message"] = smtp_message
            if not smtp_valid:
                result["reason"] = f"SMTP verification failed: {smtp_message}"
                return result
        
        # If we got here, the email is valid
        result["is_valid"] = True
        return result

def main():
    """Example usage of the EmailValidator."""
    validator = EmailValidator()
    
    print("Email Validator Test")
    print("====================")
    
    while True:
        email = input("\nEnter an email to validate (or 'q' to quit): ")
        if email.lower() == 'q':
            break
        
        print("\nRunning basic validation...")
        result = validator.is_valid_email(email)
        
        print(f"\nEmail: {email}")
        print(f"Valid: {result['is_valid']}")
        
        if not result['is_valid']:
            print(f"Reason: {result['reason']}")
        
        print("\nDetails:")
        for key, value in result['details'].items():
            print(f"  {key}: {value}")
        
        run_smtp = input("\nRun SMTP verification? (y/n): ").lower() == 'y'
        if run_smtp:
            print("\nRunning SMTP verification (this may take a few seconds)...")
            result = validator.is_valid_email(email, check_smtp=True)
            
            print(f"\nSMTP Valid: {result['details'].get('smtp_valid', 'Not checked')}")
            print(f"SMTP Message: {result['details'].get('smtp_message', 'Not checked')}")

if __name__ == "__main__":
    main() 