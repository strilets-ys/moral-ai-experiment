# Moral AI Experiment

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## About the Study

This experiment investigates whether conversations with AI can influence people's moral judgments on ethical dilemmas. Participants:

1. Complete a personality assessment (TIPI - Ten-Item Personality Inventory)
2. Rate 8 moral dilemmas on a scale from "morally wrong" to "morally acceptable"
3. Discuss 4 of those dilemmas with an AI that argues the opposite position
4. Re-rate the same dilemmas after the discussions
5. Provide feedback on their experience

### Experimental Conditions

Participants are randomly assigned to one of three conditions:

| Condition | Description |
|-----------|-------------|
| **Neutral** | AI presents thoughtful counterarguments without active persuasion |
| **Persuade** | AI actively attempts to change the participant's moral judgment |
| **Persuade + Info** | AI uses personality data to tailor its persuasive approach |

### LLM Providers

The study compares three different language models:
- OpenAI GPT-x
- Anthropic Claude
- Alibaba Qwen

## Tech Stack

- **Backend:** Django 5.x
- **Database:** SQLite (development)
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **LLM Integration:** OpenAI, Anthropic, and Qwen APIs

## Quick Start

### Prerequisites

- Python 3.10+
- At least one LLM API key (OpenAI, Anthropic, or Qwen)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/moral-ai-experiment.git
cd moral-ai-experiment

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API key(s)

# Initialize database
python manage.py migrate
python manage.py load_dilemmas

# Run development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to start the experiment.

See [SETUP.md](SETUP.md) for detailed setup and testing instructions.

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
├── .env.example             # Environment variables template
└── SETUP.md                 # Detailed setup instructions
```

## Data Collected

| Data Type | Description |
|-----------|-------------|
| Personality | TIPI responses (Big Five traits) |
| Moral Ratings | Pre/post ratings on 8 dilemmas (1-7 scale) |
| Chat Transcripts | Full conversation history with AI |
| Event Logs | Page views, timing data, interactions |
| Debrief | Participant feedback and self-reported opinion changes |

## Participant Flow

```
Landing → Consent → TIPI Survey → Pre-Rating → Chat (×4) → Post-Rating → Debrief → Complete
```

Each stage has a timer to ensure consistent data collection across participants.

## License

This project is part of academic research. Please contact the authors before using or adapting this code.

## Acknowledgments

Developed as part of a thesis project investigating AI influence on moral judgements.
