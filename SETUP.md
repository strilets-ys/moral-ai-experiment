# Moral AI Experiment - Setup Instructions

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## Project Overview

This experiment:
1. Collects participant personality data (TIPI survey)
2. Gets baseline moral ratings on 8 ethical dilemmas
3. Has participants discuss 4 dilemmas with an AI (which argues the opposite position)
4. Collects post-discussion ratings to measure opinion change
5. Debriefs participants

**Three experimental conditions:**
- `neutral` - AI presents thoughtful counterarguments
- `persuade` - AI actively tries to persuade
- `persuade_info` - AI uses personality data to tailor persuasion

**Three LLM providers:** OpenAI (GPT-4), Anthropic (Claude), Qwen

---

## Local Setup

### 1. Create Virtual Environment

```bash
cd website_for_experiment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install python-dotenv  # Optional but recommended for env management
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# At minimum, configure ONE of these for testing:
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
QWEN_API_KEY=your-qwen-key

# Optional - Qwen uses this base URL by default:
# QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# For Prolific integration (not needed for standalone testing):
# PROLIFIC_COMPLETION_URL=https://app.prolific.com/submissions/complete?cc=YOURCODE
```

**Getting API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys
- Qwen/Aliyun: https://dashscope.console.aliyun.com/

If using `python-dotenv`, add this to the top of `moralai/settings.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 4. Initialize Database

```bash
python manage.py migrate
python manage.py load_dilemmas
python manage.py createsuperuser  # Optional - for admin access
```

### 5. Run Development Server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## Testing the Flow

### Manual Testing Checklist

1. **Landing page** (`/`) - Should create a new participant
2. **Consent** (`/consent/`) - Accept to continue
3. **TIPI Survey** (`/tipi/`) - 10 personality questions (2 min timer)
4. **Pre-rating** (`/pre-rating/`) - Rate all 8 dilemmas (7 min timer)
5. **Chat** (`/chat/0/` through `/chat/3/`) - 4 AI discussions (5 min each)
6. **Post-rating** (`/post-rating/`) - Re-rate all 8 dilemmas (5 min timer)
7. **Debrief** (`/debrief/`) - Feedback form
8. **Complete** (`/complete/`) - Success page

### Admin Panel

Access at: http://127.0.0.1:8000/admin/

View and manage:
- Participants and their assigned conditions
- Ratings (pre/post)
- Chat transcripts
- Event logs

---

## Testing Specific Conditions/LLMs

Currently, condition and LLM provider are randomly assigned. For testing a specific configuration, you can temporarily modify `experiment/views.py` in the `landing()` function.

Find this section:
```python
condition = random.choice(['neutral', 'persuade', 'persuade_info'])
llm_provider = random.choice(['openai', 'anthropic', 'qwen'])
```

Change to force specific values:
```python
condition = 'persuade'  # or 'neutral' or 'persuade_info'
llm_provider = 'anthropic'  # or 'openai' or 'qwen'
```

**Remember to revert this before actual data collection!**

---

## Project Structure

```
website_for_experiment/
├── moralai/                 # Django project settings
│   ├── settings.py          # Configuration (API keys, database)
│   └── urls.py              # Root URL routing
├── experiment/              # Main app
│   ├── models.py            # Database models
│   ├── views.py             # Page and API views
│   ├── llm.py               # LLM client implementations
│   ├── admin.py             # Admin panel configuration
│   ├── templates/           # HTML templates
│   ├── static/              # CSS and JavaScript
│   └── management/commands/ # Django commands (load_dilemmas)
├── requirements.txt         # Python dependencies
├── manage.py               # Django CLI
└── db.sqlite3              # SQLite database (created after migrate)
```

---

## Troubleshooting

### "API key not set" or empty responses
- Check that the environment variable is set: `echo $OPENAI_API_KEY`
- If using `.env` file, ensure `python-dotenv` is installed and loaded in settings.py

### Chat not streaming / connection errors
- Verify API key is valid and has credits
- Check browser console for JavaScript errors
- Check Django server logs for Python exceptions

### Database errors
- Run `python manage.py migrate` to ensure tables exist
- Run `python manage.py load_dilemmas` to populate dilemmas

### Participant stuck / can't proceed
- Check admin panel for participant status
- Clear browser cookies/session to start fresh
- Or delete participant from admin and try again

---

## Current Limitations (TODO)

- [ ] No graceful handling when API key is missing
- [ ] No way to select condition/LLM via URL parameters for testing
- [ ] No data export functionality yet
- [ ] Production deployment not configured (DEBUG=True, SQLite, etc.)

---

## Data Collected

Per participant:
- Prolific ID (if provided)
- Assigned condition and LLM provider
- TIPI personality responses (10 items)
- Pre and post moral ratings (8 dilemmas × 2 phases)
- Full chat transcripts (4 conversations)
- Event logs (page views, timer events, etc.)
- Debrief responses
