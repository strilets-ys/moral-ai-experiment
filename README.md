# Moral AI Experiment

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## About the Study

This experiment investigates whether conversations with AI can influence people's moral judgments on ethical dilemmas. Participants:

1. Complete a personality assessment (TIPI - Ten-Item Personality Inventory)
2. Rate 9 moral dilemmas on a scale from "morally wrong" to "morally acceptable"
3. Discuss 5 of those dilemmas with an AI (2 same stance, 2 opposite stance, 1 random)
4. Re-rate the same dilemmas after the discussions (in a different order)
5. Provide feedback on their experience

### Stance Assignment System

The AI's position relative to the participant is controlled through a **balanced stance assignment system**:

- **4 moral dilemmas**: Randomly split 2+2 (2 same stance as participant, 2 opposite stance)
- **1 nonmoral dilemma**: Random stance (pro or contra)
- **6 combinations**: Balanced across participants to ensure equal distribution

The AI's goal depends on its position:
- **Pro (same stance)**: Reinforce and polarize - strengthen the participant's existing view
- **Contra (opposite stance)**: Persuade - challenge the participant to change their position

### Zero-Shot Ethical Framework Argumentation

The AI uses **zero-shot learning** - it is only told which ethical framework to argue from (deontological/utilitarian) without explicit instructions on how to apply it:
- The AI presents arguments naturally without naming the ethical framework
- Framework assignment is based on the dilemma type and participant's rating

### Experimental Conditions

Participants are randomly assigned to one of three conditions:

| Condition | Description |
|-----------|-------------|
| **Neutral** | AI argues position without active persuasion |
| **Persuade** | AI actively attempts to change or reinforce the participant's moral judgment |
| **Persuade + Info** | AI uses personality data (Big Five) to tailor its approach |

### LLM Providers

The study supports multiple language models:
- **Qwen3** (via vLLM) - Currently active
- OpenAI GPT-4 (requires API key)
- Anthropic Claude (requires API key)

### Moral Dilemmas (22 total)

Dilemmas are drawn from two sources:

**Greene Dilemmas (6)**
| Category | Type | Description |
|----------|------|-------------|
| Personal | Action | Footbridge-style dilemma |
| Personal | Omission | Personal harm by inaction |
| Impersonal | Action | Trolley-style dilemma |
| Impersonal | Omission | Impersonal harm by inaction |
| Nonmoral | - | 2 non-ethical decision scenarios |

**Koerner Dilemmas (16 = 4 base × 4 variations)**
| Base Dilemma | Variations |
|--------------|------------|
| 4 scenarios | BenefitsGreater-Prohibition, BenefitsSmaller-Prohibition, BenefitsGreater-Prescription, BenefitsSmaller-Prescription |

For each participant:
- **9 dilemmas rated**: All 4 Greene moral + 1 nonmoral + 4 Koerner (1 per variation type)
- **5 dilemmas discussed**: 1 personal + 1 impersonal + 1 nonmoral + 2 Koerner (same cost category)

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

- **Balanced Stance Assignment**: 6 stance combinations balanced across participants (2 same + 2 opposite per participant)
- **Context-Aware Goals**: LLM receives user's position and rating (e.g., "User believes action is morally wrong (rated 2/7)")
- **Zero-Shot Learning**: AI applies ethical frameworks based on pre-trained knowledge
- **AI-First Conversations**: The AI initiates each discussion by sharing its perspective
- **Minimum Chat Engagement**: Participants must send at least 3 messages before proceeding
- **Nonsensical Input Handling**: LLM asks for clarification when receiving unclear messages
- **Attention Check**: Random attention check during rating phase (select rating 3)
- **Streaming Responses**: Real-time token streaming for natural conversation flow
- **Different Rating Orders**: Pre and post rating use different randomized orders
- **System Prompt Logging**: All prompts sent to LLM are stored with stance mode and position
- **Data Export**: JSON/CSV export with filters at `/admin/experiment/export/`
- **Delete All Data**: Admin feature to clear all participant data with confirmation
- **Read-Only Admin**: Prevents accidental data modification (except GDPR deletion)
- **Timed Sessions**: Each page has a timer (non-intrusive - shows warning instead of auto-redirecting)
- **Personality-Tailored Persuasion**: Persuade+Info condition uses Big Five traits
- **LLM Connection Test**: Connection verified after consent, shows 503 error if unavailable

## Data Collected

| Data Type | Description |
|-----------|-------------|
| Personality | TIPI responses (Big Five traits as percentages) |
| Demographics | Age, gender, education, native English speaker |
| Moral Ratings | Pre/post ratings on 9 dilemmas (1-7 scale) |
| Chat Transcripts | Full conversation history with AI (5 discussions) |
| System Prompts | Prompts sent to LLM with stance mode and position |
| Stance Assignments | Which dilemmas had same vs opposite stance |
| Attention Check | Pass/fail status and response given |
| Event Logs | Page views, timing data, interactions |
| AI Usage | Frequency of generative AI use, tools used, AI trust level |
| Debrief | Participant feedback, persuasion awareness, opinion changes |

## Database Models

| Model | Purpose |
|-------|---------|
| `Participant` | Core participant record with condition, LLM provider, stance assignments |
| `Dilemma` | Moral dilemmas with author, category, variation type, framework mappings |
| `StanceCombination` | Tracks usage of 6 stance combinations for balancing |
| `Rating` | Pre/post ratings (1-7 scale) |
| `ChatTurn` | Individual messages in AI conversations |
| `TIPIResponse` | 10-item personality questionnaire responses |
| `SystemPromptLog` | System prompts with stance_mode and llm_position |
| `EventLog` | Page views, timer events, errors |
| `DebriefResponse` | Post-study feedback |

## Participant Flow

```
Landing → Consent → LLM Test → TIPI Survey → Pre-Rating (×9 + attention check) → Chat (×5) → Post-Rating (×9) → Debrief → Complete
```

**Estimated time: 45-55 minutes**

### Timing Per Page
| Page | Time Limit |
|------|------------|
| TIPI Survey | 2 minutes |
| Pre-Rating (per dilemma) | 75 seconds |
| Chat (per discussion) | 4.5 minutes |
| Post-Rating (per dilemma) | 30 seconds |
| Debrief | 5 minutes |

- AI starts each chat discussion
- Participants must send at least 3 messages per chat before proceeding
- Timers show warning message at 0:00 (no auto-redirect)
- Chat messages saved when moving to next dilemma
- Connection to assigned LLM tested after consent
- Pre and post rating use different randomized orders
- Chat dilemma order is randomized (varies pro/contra sequence)
- Attention check appears randomly in either pre or post rating phase
- Rating of 4 = morally neutral (not undecided)

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/

**Features:**
- View participants with inline ratings, chat turns, and system prompts
- Readable dilemma assignments showing which dilemmas each participant had
- Stance combination descriptions (what each combination means)
- View system prompts sent to LLM with stance mode and position
- Delete individual participants (GDPR compliance) with audit logging
- Delete ALL participant data at `/admin/experiment/delete-all/`
- Export data to JSON/CSV at `/admin/experiment/export/`
- Attention check results visible in participant list

## License

This project is part of academic research. Please contact the authors before using or adapting this code.

## Acknowledgments

Developed as part of a thesis project investigating AI influence on moral judgments.
