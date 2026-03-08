Q-Closer

AI-powered sales call assistant that analyzes sales conversations using the SPIN Selling framework and generates coaching feedback and follow-up messages.

The system helps salespeople understand:

- what happened in the call
- what the buyer actually needs
- how strong the buying signals are
- what the salesperson did well or poorly
- what message to send next
- what questions to ask to move the deal forward

====

Core Idea:

Sales conversations contain a huge amount of information about the buyer's needs and motivations.

Q-Closer converts sales call recordings → structured insights using AI agents.

The platform automatically:

1. Transcribes the call
2. Analyzes buyer psychology
3. Evaluates salesperson performance
4. Generates a suggested follow-up message
5. Provides a plan for the next conversation

====

Architecture

The system is split into two services.

1. Django Backend (qcloser-server)

Responsible for:

- Authentication
- Organizations and users
- Recording uploads
- Database storage
- Pipeline orchestration
- Communication with the AI service
- Email notifications (future)

Tech stack:

- Django
- Django REST Framework
- PostgreSQL

====

2. AI Service (ai_service)

Responsible for:

- AI reasoning
- LangGraph orchestration
- Agent logic
- Prompt execution
- OpenAI integration

Tech stack:

- FastAPI
- LangGraph
- OpenAI API

====

High Level Flow:
User uploads recording
↓
Recording sent to transcription service
↓
Transcript saved
↓
AI Analysis Agent runs
↓
AI Feedback Agent runs
↓
AI Follow-up Agent runs
↓
Results stored in PostgreSQL

====

Pipeline Status:

Each recording moves through the following states:

waiting_transcription
transcribing
transcribed
analyzing
analyzed
generating_feedback
feedback_ready
generating_followup
followup_ready
done
failed

Follow-up intentionally runs after feedback.

====

AI Agents

The AI service contains three main agents.

Analysis Agent

Buyer-focused.

Based on SPIN Selling.

Produces insights about:

1. Situation Context
2. Implied Needs (problems)
3. Implications of those problems
4. Explicit Needs / buying motivations
5. Commitment level (advance / continuation / no-sale)

====

Feedback Agent

Salesperson-focused.

Evaluates how well the rep executed SPIN:

- quality of situation questions
- depth of problem questions
- implication question usage
- need-payoff effectiveness
- objection prevention vs reaction
- commitment strategy

Provides coaching suggestions for the next call.

====

Follow-up Agent

Generates structured follow-up output including:

- message to send to the client
- subject
- brief for the salesperson
- next steps
- questions to ask in the next call
- suggested closing lines

====

Storage
PostgreSQL

Stores:

- users and organizations
- call recordings
- transcripts
- analysis output
- feedback output
- follow-up output
- pipeline status

====

Fields on CallRecording include:

analysis_json
feedback_json
followup_json
transcript
transcript_json
status
error_stage
error_message
salesperson_email
client_email

====

File Storage

Currently:

audio files → local storage

Planned:

audio files → AWS S3

====

Service Communication

Django communicates with FastAPI via HTTP.

Internal requests include a service token:

X-AI-Token

Example endpoints:

POST /analyze
POST /feedback
POST /followup

====

LangGraph

LangGraph orchestrates the AI pipeline inside the AI service.

Each endpoint runs a small graph rather than one large graph.

Advantages:

- easier debugging
- easier retries
- idempotent execution
- clear boundaries between stages

Graphs:

analyze_graph
feedback_graph
followup_graph
Project Structure
My-Project/
│
├── qcloser-server/
│ ├── services/
│ │ ├── accounts/
│ │ └── conversations/
│ │
│ ├── core/
│ ├── requirements.txt
│ ├── Dockerfile
│ └── .env.docker
│
├── ai_service/
│ ├── app/
│ │ ├── main.py
│ │ ├── schemas.py
│ │ │
│ │ ├── agents/
│ │ │ ├── analyze_agent.py
│ │ │ ├── feedback_agent.py
│ │ │ └── followup_agent.py
│ │ │
│ │ ├── prompts/
│ │ │ ├── analyze_spin.md
│ │ │ ├── feedback_spin.md
│ │ │ └── followup.md
│ │ │
│ │ ├── graph/
│ │ │ ├── state.py
│ │ │ ├── analyze_graph.py
│ │ │ ├── feedback_graph.py
│ │ │ └── followup_graph.py
│ │ │
│ │ └── providers/
│ │ └── openai_provider.py
│ │
│ ├── requirements.txt
│ ├── Dockerfile
│ └── .env
│
├── docker-compose.yml
└── README.md

====

Development Setup
Requirements

Docker

Docker Compose

Python 3.10+

Run locally
docker compose up --build

Services will start:

Django API → http://localhost:8000
FastAPI AI → http://localhost:8001
Planned Features

Planned infrastructure improvements:

Celery + Redis background tasks

Kubernetes deployment

AWS EKS

AWS S3 for audio storage

AWS SES for transactional email

NotificationDelivery model for delivery tracking

Horizontal scaling of AI service

Project Status

The project is currently in MVP development phase.

The focus is on:

clean architecture

reliable AI pipelines

strong prompt design

scalable infrastructure foundations
