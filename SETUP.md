# Moral AI Experiment - Setup Instructions

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## Project Overview

This experiment:
1. Collects participant personality data (TIPI survey)
2. Gets baseline moral ratings on 9 ethical dilemmas
3. Has participants discuss 5 dilemmas with an AI (balanced stance: 2 same, 2 opposite, 1 random)
4. Collects post-discussion ratings to measure opinion change (different order than pre-rating)
5. Debriefs participants

**Three experimental conditions:**
- `neutral` - AI presents thoughtful arguments
- `persuade` - AI actively tries to persuade (contra) or polarize (pro)
- `persuade_info` - AI uses personality data to tailor its approach

**Three LLM providers:** OpenAI (GPT-4), Anthropic (Claude), Qwen

**Stance assignment system:**
- 4 moral dilemmas: 2 same stance + 2 opposite stance (6 balanced combinations)
- 1 nonmoral dilemma: random stance
- Pro position: reinforce/polarize the participant's view
- Contra position: persuade to change the participant's view

**Moral dilemmas (22 total):**
- Greene: 2 personal + 2 impersonal + 2 nonmoral
- Koerner: 4 base dilemmas × 4 variations (BenefitsGreater/BenefitsSmaller × Prohibition/Prescription)

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

# For production database (optional, defaults to SQLite):
# DATABASE_URL=postgres://user:pass@host:port/dbname
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

1. **Landing page** (`/`) - Should create a new participant with stance assignments
2. **Consent** (`/consent/`) - Accept to continue, LLM connection tested
3. **TIPI Survey** (`/tipi/`) - 10 personality questions (2 min timer)
4. **Pre-rating** (`/pre-rating/0/` through `/pre-rating/8/`) - Rate 9 dilemmas individually (75 sec each)
5. **Chat** (`/chat/0/` through `/chat/4/`) - 5 AI discussions (4.5 min each, randomized pro/contra order)
6. **Post-rating** (`/post-rating/0/` through `/post-rating/8/`) - Re-rate 9 dilemmas (30 sec each, different order)
7. **Debrief** (`/debrief/`) - Feedback form (5 min)
8. **Complete** (`/complete/`) - Success page with Prolific redirect

### Connection Error Page

If the LLM connection test fails after consent, participants see `/connection-error/` with instructions to email the researchers.

### Admin Panel

Access at: http://127.0.0.1:8000/admin/

**Features:**
- View participants and their assigned conditions (read-only)
- View ratings, chat transcripts, event logs (read-only)
- View system prompts sent to LLM (read-only)
- Delete participants (GDPR compliance) with audit logging
- Export data to JSON/CSV at `/admin/experiment/export/`

**Note:** Admin is read-only except for participant deletion to prevent accidental data modification.

---

## Data Export

### Admin Export Interface

Access at: http://127.0.0.1:8000/admin/experiment/export/

**Filter options:**
- Date range (start/end)
- Condition (neutral/persuade/persuade_info)
- Status (complete/withdrawn/in_progress)
- Exclude withdrawn participants

**Export formats:**
- **JSON**: Nested structure with all related data per participant
- **CSV**: Flattened structure (one row per participant, chat turns as JSON string)

**Data included:**
- Participant info (condition, LLM provider, status, timestamps)
- TIPI responses (raw items + computed Big Five percentages)
- Pre/Post ratings for all dilemmas
- Chat transcripts with timestamps
- System prompts sent to LLM
- Event logs
- Debrief responses

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
│   ├── admin.py             # Admin panel configuration (read-only + export)
│   ├── export.py            # Data export functions (JSON/CSV)
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
- The LLM connection is tested after consent - if it fails, participants see a 503 error page

### Database errors
- Run `python manage.py migrate` to ensure tables exist
- Run `python manage.py load_dilemmas` to populate dilemmas

### Participant stuck / can't proceed
- Check admin panel for participant status
- Clear browser cookies/session to start fresh
- Or delete participant from admin and try again

---

## Current Limitations (TODO)

- [x] ~~No graceful handling when API key is missing~~ (LLM connection tested after consent)
- [x] ~~No data export functionality~~ (JSON/CSV export at /admin/experiment/export/)
- [x] ~~Replace placeholder researcher contact info in templates~~
- [ ] No way to select condition/LLM via URL parameters for testing
- [ ] Production deployment not configured (DEBUG=True, etc.)

---

## Data Collected

Per participant:
- Prolific ID (if provided)
- Assigned condition and LLM provider
- Stance combination used (1-6) and individual stance assignments
- Koerner chat cost category (greater/smaller)
- TIPI personality responses (10 items, converted to Big Five percentages)
- Pre and post moral ratings (9 dilemmas × 2 phases, different orders)
- Full chat transcripts (5 conversations with stance mode and LLM position)
- System prompts sent to LLM with stance_mode and llm_position
- Event logs (page views, timer events, etc.)
- Debrief responses (AI usage frequency, persuasion awareness, opinion changes)

---

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

---

## Recent Changes

### Dilemma Restructuring (Latest)
- **22 dilemmas total**: 6 Greene (4 moral + 2 nonmoral) + 16 Koerner (4 base × 4 variations)
- **9 rated, 5 discussed**: Participants rate 9 dilemmas and discuss 5 with AI
- **Stance assignment system**: 6 balanced combinations (2 same + 2 opposite stance per participant)
- **Pro/Contra goals**: Pro position polarizes, Contra position persuades
- **Different rating orders**: Pre and post rating use different randomized orders
- **Randomized chat order**: Chat dilemma order is shuffled to vary pro/contra sequence
- **LLM position tracking**: SystemPromptLog now includes stance_mode and llm_position
- **StanceCombination model**: Tracks usage of combinations for balancing

### System Prompts (Zero-Shot Learning)
- **Framework naming only**: LLM receives `YOUR ETHICAL FRAMEWORK: deontological` without explanation
- **Position-based goals**: Pro position reinforces/polarizes, Contra position persuades
- **System prompt logging**: All prompts stored with stance_mode and llm_position

### Admin & Data Export
- **Read-only admin**: Prevents accidental data modification
- **GDPR deletion**: Participant deletion with audit logging
- **Export interface**: JSON/CSV export with filters at `/admin/experiment/export/`
- **Database flexibility**: Supports PostgreSQL via `DATABASE_URL` environment variable
- **StanceCombination admin**: View and manage stance combination balancing

### UI/UX Improvements
- **One dilemma at a time**: Rating pages now show individual dilemmas
- **Adjusted timers**: Pre-rating 75 sec/dilemma, Post-rating 30 sec/dilemma, Chat 4.5 min
- **Non-intrusive timers**: Timer shows warning message at 0:00 instead of auto-redirecting
- **Wider layout**: Container width increased to 1400px for better readability
- **Instruction boxes**: Clear instructions added to every page of the study
- **Collapsible AI instructions**: Debrief page shows AI prompt in collapsible section

### Balanced Assignment
- **Stance combinations**: 6 combinations balanced across participants
- **Koerner cost category**: Chat Koerner dilemmas always from same cost category
- **Condition/LLM assignment**: Balanced using participant counts per combination

### Data Collection
- **AI usage questions**: Added frequency and tasks questions to debrief (frequency is mandatory)
- **Mandatory debrief fields**: Radio button questions in debrief are now required

### Templates
- **Researcher contact info**: Updated in footer and relevant pages
