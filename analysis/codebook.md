# Codebook: AI Moral Persuasion Study

**Author:** Yevheniia Strilets
**Date:** 2026-07-17
**Study:** Can LLMs Shift Moral Judgements? Persuasion and Personalization in Human-LLM Debates

---

## Overview

- **Participants:** 24
- **Design:** Within-subjects
- **Dilemmas per participant:** 8 moral dilemmas + 1 attention check (9 rated total, 4 discussed with AI)
- **Rating scale:** 1 (Completely Wrong) to 7 (Completely Acceptable)

---

## Dilemma Naming Convention

Dilemma codes follow a structured format to encode metadata:

### Greene Dilemmas: `G_{Category}{Type}_{Name}`

| Code | Category | Type | Name |
|------|----------|------|------|
| `G_PA_Terrorist_Negotiation` | Personal | Action | Terrorist Negotiation |
| `G_PO_Submarine_Oxygen` | Personal | Omission | Submarine Oxygen |
| `G_IA_Data_Breach` | Impersonal | Action | Data Breach |
| `G_IO_Hospital_Fumes` | Impersonal | Omission | Hospital Fumes |

### Koerner Dilemmas: `K_{Variation}{Type}_{BaseName}`

| Prefix | Meaning |
|--------|---------|
| `K_bgA_` | Koerner, BenefitsGreater, Action (prohibition norm) |
| `K_bsA_` | Koerner, BenefitsSmaller, Action (prohibition norm) |
| `K_bgO_` | Koerner, BenefitsGreater, Omission (prescription norm) |
| `K_bsO_` | Koerner, BenefitsSmaller, Omission (prescription norm) |

**Base dilemma names:** Abduction, Vaccine, Construction_Site, Rawanda

**Examples:**
- `K_bgA_Vaccine` = Koerner, BenefitsGreater, Action, Vaccine scenario
- `K_bsO_Rawanda` = Koerner, BenefitsSmaller, Omission, Rawanda scenario

---

## Experimental Conditions

| Condition | Label | Description |
|-----------|-------|-------------|
| `neutral` | Control | LLM argues for its assigned stance without an explicit persuasive goal |
| `persuade` | Persuade | LLM is instructed to actively influence the participant's judgment |
| `persuade_demo` | Persuade + Demo | LLM receives participant's demographics (age, gender, education) to tailor responses |
| `persuade_info` | Persuade + Demo + Info | LLM receives demographics and TIPI personality profile to tailor responses |

---

## Participant-Level Variables

### Identifiers & Status

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `participant_id` | numeric | unique IDs | Unique participant identifier (not necessarily sequential) |
| `prolific_id` | character | unique ID | Prolific platform participant ID for recruitment tracking |
| `condition` | character | neutral, persuade, persuade_demo, persuade_info | Experimental condition assigned to participant |
| `llm_provider` | character | anthropic, qwen | AI model used: Claude (anthropic) or Qwen (qwen) |
| `status` | character | started, consent, demographics, tipi, pre_rating, chat, post_rating, debrief, complete, withdrawn, attention_failed | Last step the participant completed |
| `withdrawn` | logical | TRUE, FALSE | Whether participant withdrew from the study |
| `created_at` | datetime | timestamp | When participant record was created |
| `completed_at` | datetime | timestamp | When participant completed the study |

### Experimental Design

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `stance_combination_used` | integer | 1-6 | Which of 6 stance combination sets was assigned |
| `koerner_chat_cost_category` | character | greater, smaller | Cost category for Koerner dilemmas discussed with AI |
| `stance_assignments` | JSON | {dilemma_id: stance} | Assignment of AI stances (same/opposite) to each dilemma |
| `system_prompt_[dilemma]` | character | deontological, utilitarian | Ethical framework used in LLM system prompt for each dilemma |
| `chat_dilemma_ids` | JSON | [int, int, int, int] | 4 dilemma IDs assigned for chat phase |
| `pre_dilemma_order` | JSON | [int, ...] (8 items) | Dilemma IDs in random order for pre-rating |
| `post_dilemma_order` | JSON | [int, ...] (8 items) | Dilemma IDs in different random order for post-rating |
| `current_chat_index` | integer | 0-3 | Which chat discussion participant is on |

**Stance Combinations (6 total):**
1. Greene=same, Koerner=opposite
2. Koerner=same, Greene=opposite
3. Personal+K1=same, Impersonal+K2=opposite
4. Impersonal+K2=same, Personal+K1=opposite
5. Personal+K2=same, Impersonal+K1=opposite
6. Impersonal+K1=same, Personal+K2=opposite

### Demographics

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `demographics_age` | numeric | 18-120 | Participant's age in years |
| `demographics_gender` | character | male, female, non_binary, prefer_not_to_say, other | Self-reported gender identity |
| `demographics_gender_other` | character | free text | Custom gender specification (if other selected) |
| `demographics_education` | character | high_school, some_college, associate, bachelor, master, doctorate, prefer_not_to_say | Highest level of education completed |
| `demographics_native_english` | logical | TRUE, FALSE | Whether English is participant's native language |

### Personality (TIPI)

Ten-Item Personality Inventory (Gosling et al., 2003) - brief measure of Big Five personality traits. Each trait score is derived from 2 items (one regular, one reverse-scored).

**Raw Items (1-7 scale):**

| Variable | Description |
|----------|-------------|
| `tipi_item_1` | Extraverted, enthusiastic |
| `tipi_item_2` | Critical, quarrelsome (reversed for Agreeableness) |
| `tipi_item_3` | Dependable, self-disciplined |
| `tipi_item_4` | Anxious, easily upset (reversed for Emotional Stability) |
| `tipi_item_5` | Open to new experiences, complex |
| `tipi_item_6` | Reserved, quiet (reversed for Extraversion) |
| `tipi_item_7` | Sympathetic, warm |
| `tipi_item_8` | Disorganized, careless (reversed for Conscientiousness) |
| `tipi_item_9` | Calm, emotionally stable |
| `tipi_item_10` | Conventional, uncreative (reversed for Openness) |

**Derived Trait Scores (computed):**

| Variable | Formula | Description |
|----------|---------|-------------|
| `tipi_extraversion` | (item_1 + (8-item_6))/2 | Extraversion: sociable, assertive, energetic |
| `tipi_agreeableness` | ((8-item_2) + item_7)/2 | Agreeableness: cooperative, trusting, helpful |
| `tipi_conscientiousness` | (item_3 + (8-item_8))/2 | Conscientiousness: organized, responsible, dependable |
| `tipi_emotional_stability` | ((8-item_4) + item_9)/2 | Emotional Stability: calm, stable vs. neurotic |
| `tipi_openness` | (item_5 + (8-item_10))/2 | Openness to Experience: creative, curious |

### Attention Checks

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `attention_check_position_pre` | integer | 0-8 | Position of attention check in pre-rating sequence (0-indexed) |
| `attention_check_position_post` | integer | 0-8 | Position of attention check in post-rating sequence (0-indexed) |
| `attention_check_response_pre` | integer | 1-7 | Participant's response to pre-rating attention check |
| `attention_check_response_post` | integer | 1-7 | Participant's response to post-rating attention check |
| `attention_check_correct_pre` | logical | TRUE, FALSE | Whether pre-rating attention check was answered correctly (correct = 3) |
| `attention_check_correct_post` | logical | TRUE, FALSE | Whether post-rating attention check was answered correctly (correct = 5) |

### Debrief

**S-TIAS Trust Scale:**

| Variable | Type | Range | Description |
|----------|------|-------|-------------|
| `debrief_stias_confident` | integer | 1-7 | "I am confident in the AI assistant" |
| `debrief_stias_reliable` | integer | 1-7 | "The AI assistant is reliable" |
| `debrief_stias_trust` | integer | 1-7 | "I can trust the AI assistant" |
| `debrief_stias_average` | numeric | 1-7 | Average of 3 STIAS items (computed) |

**AI Usage History:**

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `debrief_ai_usage_frequency` | character | never, rarely, sometimes, often, very_often | How often participant uses generative AI |
| `debrief_ai_tools_used` | character | comma-separated | Which AI tools used (ChatGPT, Claude, Gemini, etc.) |
| `debrief_ai_usage_tasks` | character | free text | What tasks they use AI for |

**Study Feedback:**

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `debrief_noticed_persuasion` | logical | TRUE, FALSE | Whether participant noticed AI was attempting to persuade them |
| `debrief_persuasion_description` | character | free text | Participant's description of perceived persuasion attempts |
| `debrief_changed_mind` | logical | TRUE, FALSE | Whether participant self-reported changing their mind during the study |
| `debrief_change_description` | character | free text | Participant's explanation of why they changed their mind |
| `debrief_general_feedback` | character | free text | Open-ended general feedback about the study |
| `debrief_results_email` | character | email | Email address if participant wants to receive study results |

### System Data

| Variable | Type | Description |
|----------|------|-------------|
| `session_key` | character | Unique Django session identifier |
| `system_prompts` | JSON/text | System prompts used for each dilemma conversation |
| `events` | JSON/text | Log of participant events/interactions during the study |

---

## Chat Turn Data

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `participant_id` | numeric | | Link to participant |
| `dilemma_id` | numeric | | Link to dilemma |
| `sender` | character | user, ai | Who sent the message |
| `text` | text | | Message content |
| `timestamp` | datetime | | When message was sent (client-side) |

---

## System Prompt Log

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `participant_id` | numeric | | Link to participant |
| `dilemma_id` | numeric | | Link to dilemma |
| `prompt_text` | text | | Full system prompt sent to LLM |
| `condition` | character | neutral, persuade, persuade_demo, persuade_info | Experimental condition |
| `llm_framework` | character | deontological, utilitarian | Ethical framework LLM argues for |
| `stance_mode` | character | same, opposite | Relationship to participant's initial stance |
| `llm_position` | character | pro, contra | Whether LLM argues action is acceptable or wrong |
| `personality_profile` | text | | Big Five scores as text (only for persuade_info) |
| `created_at` | datetime | | Timestamp |

### System Prompt Personalization by Condition

| Condition | Personalization |
|-----------|-----------------|
| `neutral` | No personalization, basic ethical framework instruction |
| `persuade` | Adds explicit persuasion goal statement |
| `persuade_demo` | Adds demographic information (age, gender, education) |
| `persuade_info` | Adds demographics AND Big Five personality profile |

---

## Event Log

| Variable | Type | Description |
|----------|------|-------------|
| `participant_id` | numeric | Link to participant |
| `event_type` | character | Type of event (see below) |
| `page` | character | Which page event occurred on |
| `data` | JSON | Event-specific data payload |
| `timestamp` | datetime | When event occurred |

### Event Types

| Event | Description |
|-------|-------------|
| `experiment_started` | Participant begins study |
| `llm_connection_failed` | LLM connection test failed |
| `consent_given` | Participant consented |
| `consent_withdrawn` | Participant withdrew consent |
| `demographics_completed` | Demographics form submitted |
| `tipi_completed` | TIPI questionnaire submitted |
| `phase1_instructions_acknowledged` | Pre-rating instructions acknowledged |
| `phase2_instructions_acknowledged` | Chat phase instructions acknowledged |
| `phase3_instructions_acknowledged` | Post-rating instructions acknowledged |
| `attempted_attention_check_modification` | Attempt to re-answer attention check |
| `attempted_rating_modification` | Attempt to re-answer dilemma rating |
| `attention_check_completed` | Attention check response recorded |
| `both_attention_checks_failed` | Both pre and post attention checks failed |
| `pre_rating_completed` | Pre-rating phase finished |
| `post_rating_completed` | Post-rating phase finished |
| `chat_turn_saved` | Chat message saved |
| `missing_pre_rating` | System detected missing pre-rating |
| `timer_expired` | Page timer expired |
| `withdrawal` | Participant withdrew from study |
| `debrief_completed` | Debrief form submitted |
| `experiment_completed` | Study marked complete |

### Event Data Payloads

| Event | Data Fields |
|-------|-------------|
| `experiment_started` | prolific_id, condition, llm_provider |
| `llm_connection_failed` | provider, error |
| `demographics_completed` | age, gender, education |
| `tipi_completed` | item_1 through item_10 |
| `attention_check_completed` | phase, response, required, passed, position |
| `both_attention_checks_failed` | pre_response, pre_required, post_response, post_required |
| `attempted_attention_check_modification` | index, existing_response |
| `attempted_rating_modification` | dilemma_id, index |
| `missing_pre_rating` | dilemma_id |

---

## Rating Model

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `participant_id` | numeric | | Link to participant |
| `dilemma_id` | numeric | | Link to dilemma |
| `phase` | character | pre, post | Before or after AI discussion |
| `rating` | integer | 1-7 | Moral permissibility rating |
| `created_at` | datetime | | When rating was recorded |

---

## Dilemma-Level Variables

### Core

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `participant_id` | numeric | unique IDs | Links to participant-level data |
| `dilemma` | character | see Dilemma Naming Convention | Dilemma code (e.g., G_PA_Terrorist_Negotiation) |
| `had_chat` | logical | TRUE, FALSE | Whether participant discussed this dilemma with AI (4 per participant) |
| `rating_pre` | numeric | 1-7 | Moral permissibility rating before AI discussion |
| `rating_post` | numeric | 1-7 | Moral permissibility rating after AI discussion |
| `rating_change` | numeric | -6 to +6 | Change in rating: `rating_post - rating_pre` |
| `chat_turns` | numeric | 0+ | Number of conversation turns with AI (0 if not discussed) |

### AI Stance

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `stance_mode` | character | opposite, same | Whether AI argued opposite to or same as participant's initial position |
| `llm_framework` | character | utilitarian, deontological | Ethical framework AI was assigned to argue for |
| `low_rating_framework` | character | utilitarian, deontological | Which framework corresponds to a LOW rating (1) on this dilemma |
| `ai_argues_for` | character | utilitarian, deontological | The ethical position AI advocated for |

### Outcomes

| Variable | Type | Values | Description |
|----------|------|--------|-------------|
| `outcome` | character | Moved toward AI, Backfired, No Change | Persuasion outcome (only for discussed dilemmas) |
| `moved_toward_ai` | logical | TRUE, FALSE | Whether participant's rating moved toward AI's advocated position |

---

## Dilemma Metadata

### Category Definitions

- **Personal (P):** Direct physical involvement in causing harm (e.g., pushing someone)
- **Impersonal (I):** Indirect or mechanical involvement (e.g., pulling a lever)
- **Koerner (K):** Dilemmas from Koerner's norm-based framework

### Action vs Omission

- **Action (A):** Actively doing something that causes harm (e.g., pulling a switch to redirect a trolley)
- **Omission (O):** Not acting, thereby allowing harm to occur (e.g., not pulling a switch)

### Koerner Variations

- **bg (BenefitsGreater):** Benefits of the action outweigh the costs
- **bs (BenefitsSmaller):** Costs of the action outweigh the benefits
- **prohibition:** Norm forbids the action → coded as Action
- **prescription:** Norm requires the action → coded as Omission

---

## Dilemma Pool

### Greene Dilemmas (4)

| Code | Category | Type | Description |
|------|----------|------|-------------|
| `G_PA_Terrorist_Negotiation` | Personal | Action | Breaking terrorist's son's arm to stop bombing |
| `G_PO_Submarine_Oxygen` | Personal | Omission | Not killing injured crew member to save oxygen |
| `G_IA_Data_Breach` | Impersonal | Action | Sharing confidential information for debt relief |
| `G_IO_Hospital_Fumes` | Impersonal | Omission | Not hitting switch, letting 3 patients die |

### Koerner Dilemmas (16 = 4 base scenarios × 4 variations)

**Base scenarios:** Abduction, Vaccine, Construction_Site, Rawanda

| Variation | Code Prefix | Norm Type | Cost-Benefit | Type |
|-----------|-------------|-----------|--------------|------|
| BenefitsGreater-Prohibition | `K_bgA_` | Proscriptive | Benefits > Costs | Action |
| BenefitsSmaller-Prohibition | `K_bsA_` | Proscriptive | Benefits < Costs | Action |
| BenefitsGreater-Prescription | `K_bgO_` | Prescriptive | Benefits > Costs | Omission |
| BenefitsSmaller-Prescription | `K_bsO_` | Prescriptive | Benefits < Costs | Omission |

### Dilemma Selection Per Participant

- **Rated:** 8 dilemmas + 1 attention check = 9 total
  - All 4 Greene dilemmas
  - 4 Koerner dilemmas (1 per variation type)
- **Discussed with AI:** 4 dilemmas
  - 1 personal (Greene)
  - 1 impersonal (Greene)
  - 2 Koerner (same cost category)

---

## Derived Variables (calculated in analysis)

| Variable | Formula | Description |
|----------|---------|-------------|
| `movement_toward_ai` | See below | Signed movement: positive = moved toward AI, negative = backfired |
| `abs_change` | `abs(rating_change)` | Absolute magnitude of rating change |
| `is_claude` | `llm_provider == "anthropic"` | Binary: 1 = Claude, 0 = Qwen |
| `is_opposing` | `stance_mode == "opposite"` | Binary: 1 = AI argued opposite stance |
| `is_persuasion` | `condition != "neutral"` | Binary: 1 = persuasion condition |
| `is_personalized` | `condition %in% c("persuade_demo", "persuade_info")` | Binary: 1 = personalized persuasion |

### Movement Toward AI Calculation

```r
movement_toward_ai = case_when(
  outcome == "Moved toward AI" ~ abs(rating_change),
  outcome == "Backfired" ~ -abs(rating_change),
  TRUE ~ 0
)
```

- **Positive values:** Participant moved toward AI's position (persuasion success)
- **Negative values:** Participant moved away from AI's position (backfire effect)
- **Zero:** No change in rating

---

## Rating Scale Notes

- Scale: 1 (Completely Wrong) to 7 (Completely Acceptable)
- Measures moral permissibility of the action in each dilemma
- The meaning of low vs. high ratings varies by dilemma
- `low_rating_framework` indicates whether a rating of 1 aligns with utilitarian or deontological reasoning
- This allows consistent coding of "movement toward AI" regardless of which direction the AI argued

---

## Data Files

| File | Level | Rows | Description |
|------|-------|------|-------------|
| `data` | Participant | 24 | One row per participant with demographics, personality, condition |
| `data_long` | Dilemma | 192 | One row per participant × dilemma (24 × 8 = 192) |
| `data_chat_analysis` | Discussed dilemmas | 96 | Subset where `had_chat == TRUE` (24 × 4 = 96) |

---

## Notes

- Columns containing "train", "shower", or "bus" dilemmas were removed (not used in final study)
- Dilemma codes were renamed from original names to structured format during analysis

---
