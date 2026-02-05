# services/conversations/analysis_service.py

import os
from typing import Optional

from openai import OpenAI

from .models import CallRecording

client = OpenAI()

# Generic, neutral B2C sales guidelines for POC
BASE_SALES_GUIDELINES = """
You are analyzing a B2C sales conversation (seller talking to an individual consumer).

A solid B2C sales conversation usually:
- Builds quick rapport and trust.
- Understands the customer's personal context, needs, pains, or desires.
- Clarifies what matters most to the customer (price, convenience, quality, speed, emotion, status, etc.).
- Connects the product or service clearly to those needs and motivations.
- Handles doubts and objections calmly (price concerns, trust, timing, alternatives).
- Makes the next step simple and clear (trial, purchase, follow-up, scheduling).
- Avoids pressure and stays helpful, honest, and human.

Your analysis should:
- Stay neutral and not assume any specific industry.
- Focus on clarity and practical advice that can help improve conversion and retention.
"""


def build_analysis_prompt(
    recording: CallRecording,
    playbook_text: Optional[str] = None,
) -> str:
    org_name = recording.org.name if recording.org else "Unknown Org"
    deal_title = recording.deal_title or "Untitled Conversation"

    guidelines = playbook_text or BASE_SALES_GUIDELINES

    return f"""
You are a senior B2C sales coach helping a salesperson improve their calls.

Brand / organization: {org_name}
Context label: {deal_title}

Sales guidelines for this analysis:
{guidelines}

Here is the full call transcript (it may contain automatic transcription errors):

---------------- TRANSCRIPT START ----------------
{recording.transcript}
---------------- TRANSCRIPT END ----------------

Please return a concise, neutral, practical analysis in clear markdown
with exactly these sections:

## Golden Nuggets
3–5 short bullets with concrete insights that will help move this customer closer to purchase
or reduce the risk of losing them.

## Key Patterns
- What was done well in this conversation.
- What seemed missing, weak, confusing, or risky from a B2C perspective.

## Next Conversation Recommendation
1–3 bullet points on what the salesperson should focus on or ask in the next interaction
(call, message, or meeting).

## Purchase / Closing Outlook
A short paragraph about:
- How likely the customer is to buy based on this call.
- Main doubts or risks.
- What is needed to move them toward a successful purchase.
"""


def analyze_call_recording(
    recording: CallRecording,
    playbook_text: Optional[str] = None,
) -> str:
    if not recording.transcript:
        raise ValueError("Recording has no transcript yet.")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    prompt = build_analysis_prompt(recording, playbook_text=playbook_text)

    response = client.chat.completions.create(
        model=model_name,
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": "You are a neutral, practical B2C sales coach and call analyst.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content
    return content or ""
