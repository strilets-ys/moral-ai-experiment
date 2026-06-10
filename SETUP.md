# Moral AI Experiment - Setup Instructions

A Django web application for researching how AI-assisted discussions influence human moral judgment.

## Project Overview

This experiment:
1. Collects participant demographics and personality data (TIPI survey)
2. Gets baseline moral ratings on 8 ethical dilemmas (Phase 1)
3. Has participants discuss 4 dilemmas with an AI (Phase 2)
4. Collects post-discussion ratings to measure opinion change (Phase 3)
5. Debriefs participants and provides completion code

**Four experimental conditions:**
- `neutral` - AI presents thoughtful arguments
- `persuade` - AI actively tries to persuade (contra) or polarize (pro)
- `persuade_demo` - AI uses demographic data to personalize its approach
- `persuade_info` - AI uses demographic + personality data to personalize its approach

**Two LLM providers (randomly assigned):**
- Anthropic (Claude Opus 4.5)
- Qwen (Qwen3-30B via compatible API)

**Stance assignment system:**
- 4 moral dilemmas: 2 same stance + 2 opposite stance (6 balanced combinations)
- Pro position: reinforce/polarize the participant's view
- Contra position: persuade to change the participant's view

**Moral dilemmas (20 total):**
- Greene: 2 personal + 2 impersonal
- Koerner: 4 base dilemmas × 4 variations

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
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Configure at least ONE of these:
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
QWEN_API_KEY=your-qwen-key

# Optional - Qwen uses this base URL by default:
# QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# For completion code verification:
COMPLETION_CODE_SALT=your-secret-salt-here

# For Prolific integration:
# PROLIFIC_COMPLETION_URL=https://app.prolific.com/submissions/complete?cc=YOURCODE

# For production database (optional, defaults to SQLite):
# DATABASE_URL=postgres://user:pass@host:port/dbname
```

**Getting API Keys:**
- Anthropic: https://console.anthropic.com/settings/keys
- Qwen/Aliyun: https://dashscope.console.aliyun.com/

### 4. Initialize Database

```bash
python manage.py migrate
python manage.py load_dilemmas
python manage.py extract_protagonist_names
python manage.py init_completion_cells --target 3  # For pilot study (3 per cell)
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

1. **Landing page** (`/`) - Creates participant with balanced condition/LLM assignment
2. **Consent** (`/consent/`) - Focus warning, accept to continue
3. **Demographics** (`/demographics/`) - Age, gender, education, native English
4. **TIPI Survey** (`/tipi/`) - 10 personality questions
5. **Phase 1 Instructions** - Instructions for rating phase
6. **Pre-rating** (`/pre-rating/0/` through `/pre-rating/8/`) - Rate 8 dilemmas + 1 attention check
7. **Phase 2 Instructions** - "Phase 1 Complete!" banner, chat instructions
8. **Chat** (`/chat/0/` through `/chat/3/`) - 4 AI discussions
9. **Phase 3 Instructions** - "Phase 2 Complete!" banner, re-rating instructions
10. **Post-rating** (`/post-rating/0/` through `/post-rating/7/`) - Re-rate 8 dilemmas
11. **Debrief** (`/debrief/`) - Feedback form, study info
12. **Complete** (`/complete/`) - Completion code (MJAI-XXX-XXXX format)

### Attention Check

- Appears randomly during pre-rating or post-rating
- Correct answer: Rating 3
- Failure: Immediately redirects to `/attention-failed/` with Prolific policy notice

### Back Button Prevention

- Users are warned not to use back button in phase instructions
- Client-side: sessionStorage tracks submitted ratings
- Server-side: Existing ratings cannot be modified
- bfcache: Forces page reload on back navigation

### Admin Panel

Access at: http://127.0.0.1:8000/admin/

**Features:**
- View participants with ratings, chat transcripts, and system prompts
- **Completion Cells**: Track pilot study progress with visual progress bars
- View completion codes for each participant
- Delete individual participants (GDPR compliance) with audit logging
- Delete ALL participant data at `/admin/experiment/delete-all/`
- Export data to JSON/CSV at `/admin/experiment/export/`

---

## Management Commands

| Command | Purpose |
|---------|---------|
| `load_dilemmas` | Load moral dilemmas from fixtures |
| `extract_protagonist_names` | Extract character names from dilemma texts |
| `init_completion_cells --target N` | Initialize pilot study cells (N participants per cell) |
| `verify_completion_codes` | Verify completion codes from Prolific submissions |

---

## Data Export

### Admin Export Interface

Access at: http://127.0.0.1:8000/admin/experiment/export/

**Filter options:**
- Date range (start/end)
- Condition (neutral/persuade/persuade_demo/persuade_info)
- Status (complete/withdrawn/in_progress)
- Exclude withdrawn participants

**Export formats:**
- **JSON**: Nested structure with all related data per participant
- **CSV**: Flattened structure (one row per participant)

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
│   ├── utils.py             # Completion code functions
│   ├── admin.py             # Admin panel configuration
│   ├── export.py            # Data export functions (JSON/CSV)
│   ├── templates/           # HTML templates
│   ├── static/              # CSS and JavaScript
│   └── management/commands/ # Django commands
├── docs/                    # Documentation
│   └── INSTRUCTIONS.txt     # All participant-facing instructions
├── requirements.txt         # Python dependencies
├── manage.py               # Django CLI
└── db.sqlite3              # SQLite database (created after migrate)
```

---

## Troubleshooting

### "API key not set" or empty responses
- Check that the environment variable is set: `echo $ANTHROPIC_API_KEY`
- If using `.env` file, ensure it's being loaded in settings.py

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

### Attention check not appearing
- Check `attention_check_phase` and `attention_check_position` in admin
- Attention check appears at random position in either pre or post rating

---

## Database Models

| Model | Purpose |
|-------|---------|
| `Participant` | Core record with condition, LLM provider, stance assignments, completion code |
| `Dilemma` | Moral dilemmas with author, category, protagonist name |
| `CompletionCell` | Pilot study balancing (condition × LLM provider cells) |
| `StanceCombination` | Tracks usage of 6 stance combinations |
| `Rating` | Pre/post ratings (1-7 scale) |
| `ChatTurn` | Individual messages in AI conversations |
| `TIPIResponse` | 10-item personality questionnaire |
| `DemographicsResponse` | Age, gender, education, native English |
| `SystemPromptLog` | System prompts with stance_mode and llm_position |
| `EventLog` | Page views, timer events, errors |
| `DebriefResponse` | Post-study feedback |
