# Moral AI Experiment

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## About the Study

This experiment investigates whether conversations with AI can influence people's moral judgments on ethical dilemmas. Participants:

1. Complete a personality assessment (TIPI - Ten-Item Personality Inventory)
2. Rate 8 moral dilemmas on a scale from "morally wrong" to "morally acceptable"
3. Discuss 4 of those dilemmas with an AI that argues from the opposite ethical framework
4. Re-rate the same dilemmas after the discussions
5. Provide feedback on their experience

### Zero-Shot Ethical Framework Argumentation

The AI uses **zero-shot learning** - it is only told which ethical framework to argue from (deontological/utilitarian) without explicit instructions on how to apply it:
- The AI always argues from the **opposite ethical framework** to the participant
- If the participant is neutral (rating = 4), the AI is randomly assigned a framework
- The AI presents arguments naturally without naming the ethical framework
- Exception: Marital Affair dilemma includes explicit position due to counterintuitive utilitarian stance

### Experimental Conditions

Participants are randomly assigned to one of three conditions:

| Condition | Description |
|-----------|-------------|
| **Neutral** | AI argues from opposite framework without active persuasion |
| **Persuade** | AI actively attempts to change the participant's moral judgment |
| **Persuade + Info** | AI uses personality data (Big Five) to tailor its persuasive approach |

### LLM Providers

The study supports multiple language models:
- **Qwen3** (via vLLM) - Currently active
- OpenAI GPT-4 (requires API key)
- Anthropic Claude (requires API key)

### Moral Dilemmas

8 dilemmas from moral psychology research, each with researcher attribution:
- Tyrannicide (K), Medicine costs (K), Rugby cannibalism (K), Endowment (K)
- Marital Affair (E)
- Terrorist Negotiation (G), Crew Killing (G), Hospital Fumes (G)

## Tech Stack

- **Backend:** Django 5.x
- **Database:** SQLite (development), PostgreSQL (production via DATABASE_URL)
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **LLM Integration:** OpenAI-compatible API (vLLM), Anthropic SDK

## Quick Start

### Prerequisites

- Python 3.10+
- Access to vLLM endpoint or LLM API key

### Installation

```bash
# Clone the repository
git clone https://github.com/strilets-ys/thesis-zhenia.git
cd thesis-zhenia

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Initialize database
python manage.py migrate
python manage.py load_dilemmas

# Create admin user (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to start the experiment.

### Environment Variables

Copy `.env.example` to `.env` and configure your API keys and endpoints. See the example file for required variables.

## Project Structure

```
├── moralai/                 # Django project configuration
│   ├── settings.py          # Settings (database, API keys)
│   └── urls.py              # Root URL routing
├── experiment/              # Main application
│   ├── models.py            # Database models
│   ├── views.py             # Views and API endpoints
│   ├── llm.py               # LLM client implementations
│   ├── admin.py             # Admin panel (read-only + export)
│   ├── export.py            # Data export functions (JSON/CSV)
│   ├── templates/           # HTML templates
│   ├── static/              # CSS and JavaScript
│   └── management/commands/ # Custom Django commands
├── requirements.txt         # Python dependencies
└── README.md
```

## Key Features

- **Zero-Shot Learning**: AI applies ethical frameworks based on pre-trained knowledge
- **AI-First Conversations**: The AI initiates each discussion by sharing its perspective
- **Streaming Responses**: Real-time token streaming for natural conversation flow
- **Balanced Assignment**: Dilemmas for chat are balanced across participants
- **System Prompt Logging**: All prompts sent to LLM are stored for analysis
- **Data Export**: JSON/CSV export with filters at `/admin/experiment/export/`
- **Read-Only Admin**: Prevents accidental data modification (except GDPR deletion)
- **Timed Sessions**: Each page has a timer (non-intrusive - shows warning instead of auto-redirecting)
- **Personality-Tailored Persuasion**: Persuade+Info condition uses Big Five traits
- **LLM Connection Test**: Connection verified after consent, shows 503 error if unavailable

## Data Collected

| Data Type | Description |
|-----------|-------------|
| Personality | TIPI responses (Big Five traits as percentages) |
| Moral Ratings | Pre/post ratings on 8 dilemmas (1-7 scale) |
| Chat Transcripts | Full conversation history with AI |
| System Prompts | Prompts sent to LLM (logged for transparency) |
| Event Logs | Page views, timing data, interactions |
| AI Usage | Frequency of generative AI use and tasks |
| Debrief | Participant feedback, persuasion awareness, opinion changes |

## Database Models

| Model | Purpose |
|-------|---------|
| `Participant` | Core participant record with condition, LLM provider, status |
| `Dilemma` | Moral dilemmas with framework mappings and researcher attribution |
| `Rating` | Pre/post ratings (1-7 scale) |
| `ChatTurn` | Individual messages in AI conversations |
| `TIPIResponse` | 10-item personality questionnaire responses |
| `SystemPromptLog` | System prompts sent to LLM (for analysis) |
| `EventLog` | Page views, timer events, errors |
| `DebriefResponse` | Post-study feedback |

## Participant Flow

```
Landing → Consent → LLM Test → TIPI Survey → Pre-Rating (×8) → Chat (×4) → Post-Rating (×8) → Debrief → Complete
```

### Timing Per Page
| Page | Time Limit |
|------|------------|
| TIPI Survey | 2 minutes |
| Pre-Rating (per dilemma) | 75 seconds |
| Chat (per discussion) | 4.5 minutes |
| Post-Rating (per dilemma) | 30 seconds |
| Debrief | 5 minutes |

- AI starts each chat discussion
- Timers show warning message at 0:00 (no auto-redirect)
- Chat messages saved when moving to next dilemma
- Connection to assigned LLM tested after consent

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/

**Features:**
- View participants, ratings, chat transcripts, event logs (read-only)
- View system prompts sent to LLM
- Delete participants (GDPR compliance) with audit logging
- Export data to JSON/CSV at `/admin/experiment/export/`

## License

This project is part of academic research. Please contact the authors before using or adapting this code.

## Acknowledgments

Developed as part of a thesis project investigating AI influence on moral judgments.
