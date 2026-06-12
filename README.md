# Moral AI Experiment

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## About the Study

This experiment investigates whether conversations with AI can influence people's moral judgments on ethical dilemmas. Participants:

1. Complete a demographics questionnaire
2. Complete a personality assessment (TIPI - Ten-Item Personality Inventory)
3. Rate 9 moral dilemmas on a scale from "morally wrong" to "morally acceptable"
4. Discuss 4 of those dilemmas with an AI (2 same stance, 2 opposite stance)
5. Re-rate the same dilemmas after the discussions (in a different order)
6. Provide feedback on their experience

### Three Phases

The experiment is divided into three clear phases with instruction pages:

1. **Phase 1: Initial Ratings** - Rate 9 dilemmas (8 moral + 1 attention check)
2. **Phase 2: AI Discussion** - Discuss 4 dilemmas with AI assistant
3. **Phase 3: Final Ratings** - Re-rate 9 dilemmas (8 moral + 1 attention check)

### Stance Assignment System

The AI's position relative to the participant is controlled through a **balanced stance assignment system**:

- **4 moral dilemmas**: Randomly split 2+2 (2 same stance as participant, 2 opposite stance)
- **6 combinations**: Balanced across participants to ensure equal distribution

The AI's goal depends on its position:
- **Pro (same stance)**: Reinforce and polarize - strengthen the participant's existing view
- **Contra (opposite stance)**: Persuade - challenge the participant to change their position

### Experimental Conditions

Participants are randomly assigned to one of four conditions:

| Condition | Description |
|-----------|-------------|
| **Neutral** | AI argues position without active persuasion |
| **Persuade** | AI actively attempts to change or reinforce the participant's moral judgment |
| **Persuade + Demo** | AI uses demographic data (age, gender, education) to personalize its approach |
| **Persuade + Info** | AI uses both demographic and personality data (Big Five) to personalize its approach |

### LLM Providers

Participants are randomly assigned to one of two language models:
- **Anthropic Claude** (Opus 4.5)
- **Qwen3** (Qwen3-30B via compatible API)

Each participant is assigned to exactly one model for all their conversations.

### Pilot Study Balancing

For the pilot study (24 participants), a **pseudo-randomization system** ensures balanced distribution:
- 8 cells: 4 conditions × 2 LLM providers
- 3 participants per cell
- Inverse-weight sampling prioritizes under-filled cells

### Moral Dilemmas (20 total)

Dilemmas are drawn from two sources:

**Greene Dilemmas (4)**
| Category | Type | Description |
|----------|------|-------------|
| Personal | Action | Footbridge-style dilemma |
| Personal | Omission | Personal harm by inaction |
| Impersonal | Action | Trolley-style dilemma |
| Impersonal | Omission | Impersonal harm by inaction |

**Koerner Dilemmas (16 = 4 base × 4 variations)**
| Base Dilemma | Variations |
|--------------|------------|
| 4 scenarios | BenefitsGreater-Prohibition, BenefitsSmaller-Prohibition, BenefitsGreater-Prescription, BenefitsSmaller-Prescription |

For each participant:
- **9 dilemmas rated**: All 4 Greene moral + 4 Koerner (1 per variation type) + 1 attention check
- **4 dilemmas discussed**: 1 personal + 1 impersonal + 2 Koerner (same cost category)

## Tech Stack

- **Backend:** Django 5.x
- **Database:** SQLite (development), PostgreSQL (production via DATABASE_URL)
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **LLM Integration:** Anthropic SDK, OpenAI-compatible API (for Qwen)

## Quick Start

### Prerequisites

- Python 3.10+
- Access to Anthropic API or Qwen API

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
python manage.py extract_protagonist_names
python manage.py init_completion_cells --target 3  # For pilot study

# Create admin user (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to start the experiment.

### Environment Variables

Copy `.env.example` to `.env` and configure:
- `ANTHROPIC_API_KEY` - For Claude
- `QWEN_API_KEY` - For Qwen

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
├── docs/                    # Documentation
│   └── INSTRUCTIONS.txt     # All participant-facing instructions
├── requirements.txt         # Python dependencies
└── README.md
```

## Key Features

- **Three Phase Structure**: Clear phase transitions with instruction pages
- **Balanced Stance Assignment**: 6 stance combinations balanced across participants
- **Pilot Study Balancing**: CompletionCell system for 4×2 condition/LLM distribution
- **Dual Attention Checks**: One in pre-rating (correct: 3), one in post-rating (correct: 5)
- **Attention Check Failure**: Only if both checks fail; immediately ends study with Prolific policy notice
- **Back Button Prevention**: Multiple layers prevent rating modification
- **Protagonist Names**: Rating questions include character names (e.g., "How morally acceptable is Emilia's action?")
- **Minimum Chat Engagement**: Participants must send at least 3 messages before proceeding
- **Streaming Responses**: Real-time token streaming for natural conversation flow
- **Different Rating Orders**: Pre and post rating use different randomized orders
- **System Prompt Logging**: All prompts sent to LLM are stored with stance mode and position
- **Data Export**: JSON/CSV export with filters at `/admin/experiment/export/`

## Participant Flow

```
Landing → Consent → Demographics → TIPI
    ↓
Phase 1 Instructions → Pre-Rating (9 dilemmas incl. attention check)
    ↓
Phase 2 Instructions → Chat (4 discussions)
    ↓
Phase 3 Instructions → Post-Rating (9 dilemmas incl. attention check)
    ↓ (both attention checks failed → Study Ended)
Debrief → Complete (redirect to Prolific)
```

**Estimated time: 45-60 minutes**

## Admin Interface

Access the Django admin at http://127.0.0.1:8000/admin/

**Features:**
- View participants with ratings, chat transcripts, and system prompts
- **Completion Cells**: Track pilot study progress (completions per condition/LLM)
- Delete individual participants (GDPR compliance) with audit logging
- Delete ALL participant data at `/admin/experiment/delete-all/`
- Export data to JSON/CSV at `/admin/experiment/export/`

## Management Commands

| Command | Purpose |
|---------|---------|
| `load_dilemmas` | Load moral dilemmas from fixtures |
| `extract_protagonist_names` | Extract character names from dilemma texts |
| `init_completion_cells --target N` | Initialize pilot study cells (N per cell) |

## License

This project is part of academic research. Please contact the authors before using or adapting this code.
