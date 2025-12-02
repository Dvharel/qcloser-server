import os
from typing import Optional, Dict

from openai import OpenAI

from .models import CallRecording

client = OpenAI()

BASE_FOLLOWUP_GUIDELINES = """
You are helping a salesperson craft follow-up communication after a B2C sales conversation.

Principles:
- Be clear, warm, and concise.
- Reflect the customer's personal needs, interests, and concerns.
- Emphasize how the product/service helps the customer specifically.
- Reduce friction: make next steps simple and easy.
- Avoid aggressive pressure; focus on helpful, honest guidance.
- The text should be easy to copy into email or WhatsApp.
"""


def build_followup_prompt(
    recording: CallRecording,
    analysis_markdown: str,
    playbook_text: Optional[str] = None,
    channel_hint: str = "email_or_whatsapp",
) -> str:
    org_name = recording.org.name if recording.org else "Unknown Org"
    deal_title = recording.deal_title or "Untitled Conversation"

    guidelines = playbook_text or BASE_FOLLOWUP_GUIDELINES

    return f"""
You are assisting a salesperson who talks to individual consumers (B2C).

Brand / organization: {org_name}
Context label: {deal_title}

General follow-up guidelines:
{guidelines}

Here is the analysis of the previous conversation:

---------------- ANALYSIS START ----------------
{analysis_markdown}
---------------- ANALYSIS END ----------------

Please produce a structured answer with these parts:

1) SHORT SUMMARY:
2–3 sentence internal summary of where the potential purchase stands
and what the customer's situation and mindset seem to be.

2) CUSTOMER FOLLOW-UP MESSAGE:
A message the salesperson can send directly to the customer.
- Tone: warm, respectful, professional.
- Style: suitable for email or WhatsApp.
- Should reference the customer's situation and gently guide toward the next step.

3) INTERNAL BRIEF FOR SALESPERSON:
A short internal note to the salesperson:
- What to remember about this customer.
- What to be careful about.
- What to aim for in the next interaction.

Return your answer exactly in this structure (plain text, not JSON):

SHORT SUMMARY:
...

CUSTOMER FOLLOW-UP MESSAGE:
...

INTERNAL BRIEF FOR SALESPERSON:
...
"""


def generate_followup_content(
    recording: CallRecording,
    analysis_markdown: str,
    playbook_text: Optional[str] = None,
) -> Dict[str, str]:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    prompt = build_followup_prompt(
        recording=recording,
        analysis_markdown=analysis_markdown,
        playbook_text=playbook_text,
    )

    response = client.chat.completions.create(
        model=model_name,
        temperature=0.5,
        messages=[
            {
                "role": "system",
                "content": "You help B2C salespeople craft clear, warm, effective follow-up communication.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    text = response.choices[0].message.content or ""

    sections = {
        "short_summary": "",
        "customer_followup_message": "",
        "internal_brief_for_salesperson": "",
    }

    current_key = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("SHORT SUMMARY"):
            current_key = "short_summary"
            continue
        if stripped.upper().startswith("CUSTOMER FOLLOW-UP MESSAGE"):
            current_key = "customer_followup_message"
            continue
        if stripped.upper().startswith("INTERNAL BRIEF FOR SALESPERSON"):
            current_key = "internal_brief_for_salesperson"
            continue

        if current_key:
            sections[current_key] += line + "\n"

    for key in sections:
        sections[key] = sections[key].strip()

    return sections
