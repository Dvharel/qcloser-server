from openai import OpenAI

client = OpenAI()

BASE_FOLLOWUP_GUIDELINES = """
You are helping a B2C sales representative follow up after a phone call.
Create communication that is:
- Warm, concise, natural, and human.
- Focused on trust, clarity, and next steps.
- Avoids pressure or pushiness.
- Highlights value, benefits, or progress.
"""

def build_followup_prompt(transcript: str, analysis: str):
    return f"""
You are an expert B2C sales assistant.

Below is the conversation transcript:
---------------------
{transcript}
---------------------

Below is the analysis of the conversation:
---------------------
{analysis}
---------------------

Based on this, produce the following:

1. **Follow-up Message (WhatsApp/Email Style)**
Short, friendly, clear.
Tone: human, helpful, approachable.
Goal: move customer one step forward.

2. **Salesperson Brief (Internal)**
- What happened
- Customer intent signals
- Where the salesperson must focus next time

3. **Closing Continuation Plan**
- The next 2–3 steps to maintain momentum
- How to reinforce closing points
- Risks to watch for

Your response MUST be structured exactly as:

## Follow-up Message
<text>

## Salesperson Brief
<text>

## Closing Continuation Plan
<text>
"""


def generate_followup(transcript: str, analysis: str) -> str:
    prompt = build_followup_prompt(transcript, analysis)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": BASE_FOLLOWUP_GUIDELINES},
            {"role": "user", "content": prompt},
        ],
    )

    return (response.choices[0].message.content or "").strip()
