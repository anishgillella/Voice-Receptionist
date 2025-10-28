"""Send emails to customers after calls."""

from __future__ import annotations

import logging
import os
from typing import Optional, List, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class EmailTemplate:
    """Email template for post-call communication."""
    subject: str
    body: str
    html_body: Optional[str] = None


class EmailSender:
    """Send emails to customers."""
    
    # Email templates
    TEMPLATES = {
        "follow_up_info": EmailTemplate(
            subject="Information You Requested - InsureFlow Solutions",
            body="""Hi {first_name},

Thank you for taking the time to speak with us today. As discussed, I've prepared some information about our insurance solutions for {company_name}.

The attached document outlines key coverage options and pricing for your business. Please review at your convenience.

If you have any questions or would like to discuss further, feel free to reach out to me directly.

Best regards,
Jennifer
InsureFlow Solutions
"""
        ),
        "meeting_request": EmailTemplate(
            subject="Let's Schedule a Meeting - InsureFlow Solutions",
            body="""Hi {first_name},

I enjoyed our conversation today. I'd like to schedule a time to discuss your insurance needs in more detail.

Please reply with your available times, and I'll send you a calendar invite.

Looking forward to connecting!

Best regards,
Jennifer
InsureFlow Solutions
"""
        ),
        "callback_reminder": EmailTemplate(
            subject="We'll Call You Back - InsureFlow Solutions",
            body="""Hi {first_name},

Thank you for your interest. I'll call you back at {phone_number} on {callback_date} at {callback_time}.

If this doesn't work for you, please let me know your preferred time.

Best regards,
Jennifer
InsureFlow Solutions
"""
        ),
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize email sender.
        
        Args:
            settings: Voice agent settings with SendGrid config
        """
        if settings:
            self.api_key = settings.sendgrid_api_key if hasattr(settings, 'sendgrid_api_key') else os.getenv("SENDGRID_API_KEY")
            self.from_email = settings.sender_email if hasattr(settings, 'sender_email') else os.getenv("SENDER_EMAIL", "noreply@insureflow.com")
            self.from_name = settings.sender_name if hasattr(settings, 'sender_name') else os.getenv("SENDER_NAME", "InsureFlow Solutions")
        else:
            self.api_key = os.getenv("SENDGRID_API_KEY")
            self.from_email = os.getenv("SENDER_EMAIL", "noreply@insureflow.com")
            self.from_name = os.getenv("SENDER_NAME", "InsureFlow Solutions")
    
    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """Send email using SendGrid API.
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            attachments: List of attachment dicts (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not configured, skipping email")
            return False
        
        try:
            # Import SendGrid here to avoid hard dependency
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            # Create mail object
            mail = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
                plain_text_content=Content("text/plain", body),
            )
            
            # Add HTML content if provided
            if html_body:
                mail.add_content(Content("text/html", html_body))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    mail.add_attachment(
                        file_content=attachment.get("content"),
                        file_type=attachment.get("type", "application/octet-stream"),
                        file_name=attachment.get("name")
                    )
            
            # Send via SendGrid
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(mail)
            
            logger.info(f"✅ Email sent to {to_email} (status: {response.status_code})")
            return response.status_code in [200, 201, 202]
        
        except ImportError:
            logger.warning("SendGrid library not installed, skipping email")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_from_template(
        self,
        to_email: str,
        to_name: str,
        first_name: str,
        company_name: str,
        template_key: str,
        **kwargs
    ) -> bool:
        """Send email using a predefined template.
        
        Args:
            to_email: Recipient email
            to_name: Recipient name
            first_name: First name for template
            company_name: Company name for template
            template_key: Key of template to use
            **kwargs: Additional template variables
            
        Returns:
            True if sent successfully
        """
        
        if template_key not in self.TEMPLATES:
            logger.error(f"Template '{template_key}' not found")
            return False
        
        template = self.TEMPLATES[template_key]
        
        # Format template with variables
        template_vars = {
            "first_name": first_name,
            "company_name": company_name,
            **kwargs
        }
        
        try:
            body = template.body.format(**template_vars)
            subject = template.subject.format(**template_vars)
            html_body = template.html_body.format(**template_vars) if template.html_body else None
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return False
        
        return self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            body=body,
            html_body=html_body
        )


# Example usage
if __name__ == "__main__":
    sender = EmailSender()
    
    # Example: Send follow-up email
    success = sender.send_from_template(
        to_email="anish@example.com",
        to_name="Anish Gillella",
        first_name="Anish",
        company_name="Test Insurance Corp",
        template_key="follow_up_info"
    )
    
    print(f"Email sent: {success}")
