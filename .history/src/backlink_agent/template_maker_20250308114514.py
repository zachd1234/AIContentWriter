import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TemplateMaker:
    """
    Class responsible for creating email templates for outreach campaigns.
    """
    
    def __init__(self):
        """
        Initialize the TemplateMaker.
        """
        logger.info("Initializing TemplateMaker")
    
    def create_template(self, template_type: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an email template based on the specified type and variables.
        
        Args:
            template_type: The type of template to create (e.g., "backlink_request", "guest_post")
            variables: Optional dictionary of variables to customize the template
            
        Returns:
            Dictionary containing the template subject and body
        """
        logger.info(f"Creating template of type: {template_type}")
        
        if variables is None:
            variables = {}
            
        # Default template parts
        subject = ""
        body = ""
        
        # Select template based on type
        if template_type == "backlink_request":
            subject = "Opportunity to collaborate with {site_name}"
            body = """
Hello {recipient_name},

I recently came across your article on {article_title} and found it very insightful.

I noticed you mentioned {topic} in your post. I've actually published a comprehensive guide on this topic that might complement your article well: {our_article_url}

Would you consider adding a link to our resource in your article? I believe it would provide additional value to your readers.

Thank you for considering my request. I look forward to potentially collaborating with you.

Best regards,
{sender_name}
{sender_company}
            """
            
        elif template_type == "guest_post":
            subject = "Guest post proposal for {site_name}"
            body = """
Hello {recipient_name},

I'm {sender_name} from {sender_company}, and I'm reaching out because I'm a regular reader of {site_name}.

I particularly enjoyed your recent article about {article_title}. The insights on {topic} were particularly valuable.

I'd like to contribute a guest post to your site on a related topic. Here are a few ideas that might interest your audience:

1. {idea_1}
2. {idea_2}
3. {idea_3}

Let me know if any of these resonate with you, or if you have other topics you'd prefer me to cover.

Thanks for your time and consideration.

Best regards,
{sender_name}
{sender_company}
            """
            
        else:
            logger.warning(f"Unknown template type: {template_type}")
            subject = "Reaching out from {sender_company}"
            body = """
Hello {recipient_name},

I hope this email finds you well.

{custom_message}

Best regards,
{sender_name}
{sender_company}
            """
        
        # Replace variables in template
        for key, value in variables.items():
            subject = subject.replace("{" + key + "}", str(value))
            body = body.replace("{" + key + "}", str(value))
        
        return {
            "subject": subject,
            "body": body.strip()
        }


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the template maker
    template_maker = TemplateMaker()
    
    # Test backlink request template
    variables = {
        "site_name": "Example Blog",
        "recipient_name": "John",
        "article_title": "10 Ways to Improve SEO",
        "topic": "backlink strategies",
        "our_article_url": "https://example.com/backlink-guide",
        "sender_name": "Sarah",
        "sender_company": "SEO Experts Inc."
    }
    
    template = template_maker.create_template("backlink_request", variables)
    
    print("Subject:", template["subject"])
    print("\nBody:")
    print(template["body"]) 