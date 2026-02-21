# Moral AI Experiment

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## About the Study

This experiment investigates whether conversations with AI can influence people's moral judgments on ethical dilemmas. Participants:

1. Complete a personality assessment (TIPI - Ten-Item Personality Inventory)
2. Rate 8 moral dilemmas on a scale from "morally wrong" to "morally acceptable"
3. Discuss 4 of those dilemmas with an AI that argues from the opposite ethical framework
4. Re-rate the same dilemmas after the discussions
5. Provide feedback on their experience

### Ethical Framework Argumentation

Each dilemma is mapped to either a **deontological** or **utilitarian** position based on the participant's rating:
- The AI always argues from the **opposite ethical framework** to the participant
- If the participant is neutral (rating = 4), the AI is randomly assigned a framework
- The AI presents arguments naturally without naming the ethical framework

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

## Tech Stack

- **Backend:** Django 5.x
- **Database:** SQLite (development)
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
│   ├── templates/           # HTML templates
│   ├── static/              # CSS and JavaScript
│   └── management/commands/ # Custom Django commands
├── requirements.txt         # Python dependencies
└── README.md
```

## Key Features

- **AI-First Conversations**: The AI initiates each discussion by sharing its perspective
- **Streaming Responses**: Real-time token streaming for natural conversation flow
- **Ethical Framework Mapping**: Each dilemma mapped to deontological/utilitarian positions
- **Client-Side Message Tracking**: Messages saved in bulk when leaving chat page
- **Timed Sessions**: Each page has a timer for consistent data collection (non-intrusive - shows warning instead of auto-redirecting)
- **Personality-Tailored Persuasion**: Persuade+Info condition uses Big Five traits (displayed as percentages)
- **LLM Connection Test**: Connection verified after consent, shows 503 error page if LLM is unavailable
- **One Dilemma at a Time**: Rating pages show dilemmas individually for focused assessment
- **Instruction Boxes**: Clear instructions provided on each page of the study

## Data Collected

| Data Type | Description |
|-----------|-------------|
| Personality | TIPI responses (Big Five traits as percentages 0-100%) |
| Moral Ratings | Pre/post ratings on 8 dilemmas (1-7 scale) |
| Chat Transcripts | Full conversation history with AI |
| Event Logs | Page views, timing data, interactions |
| AI Usage | Frequency of generative AI use and tasks |
| Debrief | Participant feedback, persuasion awareness, opinion changes |

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
| Post-Rating (per dilemma) | 45 seconds |

- AI starts each chat discussion
- Timers show warning message at 0:00 (no auto-redirect)
- Chat messages saved when moving to next dilemma
- Connection to assigned LLM tested after consent

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/ to view:
- Participants and their conditions
- Chat transcripts
- Ratings (pre and post)
- TIPI personality scores

## License

This project is part of academic research. Please contact the authors before using or adapting this code.

## Acknowledgments

Developed as part of a thesis project investigating AI influence on moral judgments.
