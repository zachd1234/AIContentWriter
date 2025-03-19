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
                 sender_email: str,
                 timeout: int,
                 debug_level: int):
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
    validator = EmailValidator(
        sender_email="test@example.com",
        timeout=10,
        debug_level=0
    )
    
    # List of emails to test
    test_emails = [
        "josh@joshstrength.com",
        "info@ancientpurity.com",
        "contact@company.com",
        "info@golfkind.com",
        "coach@eliteendurance.com",
        "join@unionfitness.com",
        "support@futurefit.co.uk",
        "privacypolicy@healthline.com",
        "tom.sansom@ruck.co.uk",
        # Additional test cases
        "nonexistent@example.com",
        "invalid-email",
        "test@mailinator.com",  # Disposable email
        "user@gmail.com",
        "hello@microsoft.com",
        "info@thisisnotarealdomainihope.com"  # Invalid domain
    ]
    
    print("Email Validation Test Results")
    print("=============================")
    
    # Table header
    print(f"{'Email':<40} | {'Valid':<5} | {'Reason':<40}")
    print("-" * 90)
    
    # Process all emails in bulk
    for email in test_emails:
        # Run basic validation
        result = validator.is_valid_email(email)
        
        # Format the output
        valid_mark = "✅" if result["is_valid"] else "❌"
        reason = result.get("reason", "Valid email") if not result["is_valid"] else ""
        
        # Print the result in table format
        print(f"{email:<40} | {valid_mark:<5} | {reason:<40}")
    
    print("\nDetailed Results:")
    print("================")
    
    # Print detailed results for each email
    for email in test_emails:
        print(f"\n{email}")
        print("-" * len(email))
        
        result = validator.is_valid_email(email)
        
        for key, value in result["details"].items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main() 