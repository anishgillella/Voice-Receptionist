"""Test email reply handling by simulating SendGrid webhook."""

import sys
sys.path.insert(0, '/Users/anishgillella/Desktop/Stuff/Projects/Voice Agent')

import asyncio


async def process_email_reply(
    customer_email: str,
    reply_text: str,
    subject: str = "Re: Information You Requested - InsureFlow Solutions"
):
    """Process an email reply as if it came from SendGrid webhook."""
    # Import here to avoid circular imports
    from backend.voice_agent.core.config import get_settings
    from backend.voice_agent.core.db import get_customer_by_email, get_customer_conversations, get_customer_emails
    from backend.voice_agent.llm.email_reply_analyzer import EmailReplyAnalyzer
    from backend.voice_agent.services.email_sender import EmailSender
    from backend.voice_agent.services.email_response_templates import EmailResponseTemplates
    
    print("=" * 70)
    print("📧 Processing Email Reply")
    print("=" * 70)
    print(f"From: {customer_email}")
    print(f"Subject: {subject}")
    print(f"Body: {reply_text}\n")
    
    settings = get_settings()
    
    # Find customer by email
    customer = get_customer_by_email(customer_email)
    if not customer:
        print(f"❌ Customer not found for email {customer_email}")
        return
    
    customer_id = customer.get("id")
    customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
    
    print(f"👤 Customer: {customer_name}")
    print(f"   Email: {customer.get('email')}")
    print(f"   Company: {customer.get('company_name')}")
    print(f"   Phone: {customer.get('phone_number')}\n")
    
    # Get context
    conversations = get_customer_conversations(customer_id, limit=1)
    previous_call_summary = conversations[0].get("summary") if conversations else None
    
    past_emails_records = get_customer_emails(customer_id, limit=10)
    past_emails = [f"From: {e['from_email']}\nTo: {e['to_email']}\nSubject: {e['subject']}\n\n{e['body']}" for e in past_emails_records]
    
    customer_profile = {
        "name": customer_name,
        "email": customer.get("email"),
        "phone": customer.get("phone_number"),
        "company": customer.get("company_name"),
        "industry": customer.get("industry"),
        "location": customer.get("location"),
    }
    
    print("📚 Context Retrieved:")
    print(f"   Previous calls: {len(conversations)}")
    print(f"   Past emails: {len(past_emails_records)}")
    if previous_call_summary:
        print(f"   Last call summary: {previous_call_summary[:100]}...\n")
    else:
        print(f"   No previous calls\n")
    
    # Analyze with LLM
    print("🤖 Analyzing email reply with LLM...")
    analyzer = EmailReplyAnalyzer(settings=settings)
    analysis = await analyzer.analyze(
        email_reply=reply_text,
        previous_call_summary=previous_call_summary,
        past_emails=past_emails,
        customer_profile=customer_profile,
    )
    
    print(f"✅ Analysis Complete:")
    print(f"   Sentiment: {analysis.sentiment}")
    print(f"   Engagement Level: {analysis.engagement_level}")
    print(f"   Interest Change: {analysis.interest_change}")
    print(f"   Customer Intent: {analysis.customer_intent}")
    print(f"   Actions: {[a.type.value for a in analysis.actions]}\n")
    
    # Execute actions
    print("🎯 Executing Recommended Actions:")
    for i, action in enumerate(analysis.actions, 1):
        print(f"\n   Action {i}: {action.type.value}")
        print(f"   Reason: {action.reason}")
        print(f"   Priority: {action.priority}")
        
        if action.type.value == "send_response":
            # Get suggested template
            template_type = EmailResponseTemplates.suggest_template(
                action.type.value,
                analysis.sentiment,
                analysis.engagement_level,
            )
            
            if template_type:
                response_body = EmailResponseTemplates.render_template(
                    template_type,
                    customer_name=customer_name,
                    agent_name="Jennifer",
                    company_name="InsureFlow Solutions",
                    topic="insurance solutions",
                    meeting_time="this Thursday",
                    callback_time="this Friday at 2 PM",
                    phone_number=customer.get("phone_number"),
                    highlight_1="20-40% savings on premiums",
                    highlight_2="Comprehensive coverage for your industry",
                    highlight_3="Personalized consultation included",
                )
                
                print(f"   Template Used: {template_type.value}")
                print(f"\n   📧 Sending Auto-Response:")
                print(f"   " + "-" * 66)
                print("   " + response_body.replace("\n", "\n   "))
                print(f"   " + "-" * 66)
                
                # Send the response
                sender = EmailSender(settings=settings)
                success = sender.send_email(
                    to_email=customer_email,
                    to_name=customer_name,
                    subject=f"Re: {subject}",
                    body=response_body,
                )
                
                if success:
                    print(f"\n   ✅ Auto-response sent successfully!")
                else:
                    print(f"\n   ❌ Failed to send auto-response")
        
        elif action.type.value == "schedule_callback":
            print(f"   📅 Scheduling callback for {customer_name}")
        
        elif action.type.value == "escalate_to_sales":
            print(f"   🔄 Escalating to sales team")
    
    print(f"\n✅ Email reply processed successfully!\n")


if __name__ == "__main__":
    # Test scenarios
    test_cases = [
        {
            "email": "anish.gillella@gmail.com",
            "reply": "Yes, I'm very interested! Can you send me more details about pricing and coverage options for tech companies?",
            "subject": "Re: Information You Requested - InsureFlow Solutions"
        },
        {
            "email": "anish.gillella@gmail.com",
            "reply": "I'm not interested in insurance right now, please remove me from your mailing list.",
            "subject": "Re: Information You Requested - InsureFlow Solutions"
        },
        {
            "email": "anish.gillella@gmail.com",
            "reply": "When is a good time to schedule a call this week?",
            "subject": "Re: Information You Requested - InsureFlow Solutions"
        }
    ]
    
    print("\n" + "=" * 70)
    print("EMAIL REPLY INTELLIGENCE SYSTEM - TEST")
    print("=" * 70 + "\n")
    
    # Run test case 1 (positive interest)
    print("TEST CASE 1: Positive Interest")
    print("-" * 70)
    asyncio.run(process_email_reply(
        test_cases[0]["email"],
        test_cases[0]["reply"],
        test_cases[0]["subject"]
    ))
    
    # Uncomment to test other scenarios:
    # print("\nTEST CASE 2: Not Interested (DNC)")
    # print("-" * 70)
    # asyncio.run(process_email_reply(
    #     test_cases[1]["email"],
    #     test_cases[1]["reply"],
    #     test_cases[1]["subject"]
    # ))
    #
    # print("\nTEST CASE 3: Meeting Request")
    # print("-" * 70)
    # asyncio.run(process_email_reply(
    #     test_cases[2]["email"],
    #     test_cases[2]["reply"],
    #     test_cases[2]["subject"]
    # ))
