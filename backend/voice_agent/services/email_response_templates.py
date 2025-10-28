"""Email response templates for automated replies."""

from __future__ import annotations

import logging
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseTemplate(str, Enum):
    """Available response templates."""
    PROPOSAL_OFFER = "proposal_offer"
    MEETING_CONFIRMATION = "meeting_confirmation"
    INFO_DELIVERY = "info_delivery"
    PAYMENT_FOLLOW_UP = "payment_follow_up"
    ENGAGEMENT_THANK_YOU = "engagement_thank_you"
    CALLBACK_SCHEDULED = "callback_scheduled"
    ESCALATION_NOTICE = "escalation_notice"


class EmailResponseTemplates:
    """Manager for email response templates."""
    
    TEMPLATES: Dict[ResponseTemplate, str] = {
        ResponseTemplate.PROPOSAL_OFFER: """Hi {customer_name},

Thank you for your interest! Based on our conversation and your needs, I've prepared a customized proposal for you.

Key highlights:
- {highlight_1}
- {highlight_2}
- {highlight_3}

I'd love to walk you through the details. Would you be available for a brief 15-minute call this week?

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.MEETING_CONFIRMATION: """Hi {customer_name},

Perfect! I'm glad you're interested. I've scheduled a call for {meeting_time} to discuss your needs in detail.

Calendar invite has been sent separately. In the meantime, if you have any questions, feel free to reach out.

Looking forward to speaking with you!

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.INFO_DELIVERY: """Hi {customer_name},

Thank you for your interest! I'm sending over the information you requested about {topic}.

The attached document covers:
- Overview of our solutions
- Case studies from similar businesses
- Pricing and options
- Next steps

Please review at your convenience, and let me know if you have any questions!

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.PAYMENT_FOLLOW_UP: """Hi {customer_name},

Great! I'm excited to help you move forward. I've prepared the final agreement and next steps for {service_name}.

Please review the attached documents and let me know if you're ready to proceed. I can have this set up by {timeline}.

Any questions? Just reply to this email!

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.ENGAGEMENT_THANK_YOU: """Hi {customer_name},

Thank you so much for your quick response and interest! I really appreciate you taking the time to engage with us.

Your feedback and questions are valuable. Let me look into the specifics and I'll follow up with you soon.

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.CALLBACK_SCHEDULED: """Hi {customer_name},

Perfect! I've scheduled a callback for {callback_time}. I'll reach out to you at {phone_number}.

In the meantime, if there's anything specific you'd like to discuss, feel free to jot it down so we make the most of our time.

Talk soon!

Best regards,
{agent_name}
{company_name}""",

        ResponseTemplate.ESCALATION_NOTICE: """Hi {customer_name},

Thank you for reaching out! Your request is important to us, and I'm connecting you with our specialist team who can better assist you.

You'll hear from {specialist_name} shortly with more detailed information and personalized solutions.

We appreciate your patience!

Best regards,
{agent_name}
{company_name}""",
    }
    
    @staticmethod
    def get_template(template_type: ResponseTemplate) -> str:
        """Get email template by type.
        
        Args:
            template_type: Type of template to retrieve
            
        Returns:
            Template string with placeholders
        """
        return EmailResponseTemplates.TEMPLATES.get(
            template_type,
            "Hi {customer_name},\n\nThank you for your reply. We'll get back to you shortly.\n\nBest regards,\n{agent_name}"
        )
    
    @staticmethod
    def render_template(
        template_type: ResponseTemplate,
        customer_name: str,
        agent_name: str = "InsureFlow Solutions",
        company_name: str = "InsureFlow Solutions",
        **kwargs
    ) -> str:
        """Render template with variables.
        
        Args:
            template_type: Type of template
            customer_name: Customer's name
            agent_name: Agent's name
            company_name: Company name
            **kwargs: Additional template variables
            
        Returns:
            Rendered template
        """
        template = EmailResponseTemplates.get_template(template_type)
        
        variables = {
            "customer_name": customer_name,
            "agent_name": agent_name,
            "company_name": company_name,
        }
        variables.update(kwargs)
        
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
    
    @staticmethod
    def suggest_template(
        action_type: str,
        sentiment: str,
        engagement_level: str,
    ) -> Optional[ResponseTemplate]:
        """Suggest best template based on analysis.
        
        Args:
            action_type: Type of action (from EmailReplyActionType)
            sentiment: Email sentiment
            engagement_level: Customer engagement level
            
        Returns:
            Suggested template type or None
        """
        if action_type == "send_response":
            if sentiment == "positive" and engagement_level == "high":
                return ResponseTemplate.ENGAGEMENT_THANK_YOU
            elif sentiment == "positive":
                return ResponseTemplate.MEETING_CONFIRMATION
            else:
                return ResponseTemplate.INFO_DELIVERY
        
        elif action_type == "schedule_callback":
            return ResponseTemplate.CALLBACK_SCHEDULED
        
        elif action_type == "send_proposal":
            return ResponseTemplate.PROPOSAL_OFFER
        
        elif action_type == "request_payment":
            return ResponseTemplate.PAYMENT_FOLLOW_UP
        
        elif action_type == "escalate_to_sales":
            return ResponseTemplate.ESCALATION_NOTICE
        
        return None
