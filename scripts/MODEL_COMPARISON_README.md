# Model Comparison for Moral AI Experiment

## Overview

Testing different Qwen models to find the best fit for the moral AI experiment. This is a zero-shot evaluation - minimal prompts without coaching on ethical frameworks or persuasion techniques.

## Current Status

- [x] Created `scripts/model_comparison.py` - testing framework
- [x] Minimal prompts configured (framework name only, no explanations)
- [x] TIPI/Big Five integration for `persuade_info` condition
- [x] Manual scoring interface with rubric
- [x] Ollama support for local testing
- [x] Updated to use real experiment dilemmas (6 dilemmas)
- [x] Updated scoring criteria (per-run scoring, added first_sentence_quality, big_five_concealment)
- [x] Run tests on all models
- [x] Score results (manual scoring complete)
- [x] Select best model: **qwen3:14b**

## Model Comparison Results

### Automated Metrics

| Model | Sentence ≤3 | No FW Terms | Avg Time | Tokens/sec |
|-------|-------------|-------------|----------|------------|
| **qwen3:14b** | **98%** ✓ | **100%** ✓ | 19.8s | 3.4 |
| qwen2.5:32b | 96% ✓ | 100% ✓ | 10.0s | 6.6 |
| qwen2.5:14b | 94% ✓ | 88% ⚠ | 4.0s | 13.8 |
| qwen2.5:7b | 79% ⚠ | 90% ⚠ | 2.5s | 20.0 |
| Qwen3VL-30B | 75% ⚠ | 100% ✓ | 1.6s | 48.4 |
| qwen3:8b | 71% ⚠ | 100% ✓ | 13.5s | 5.6 |

### Manual Quality Scores (0-3 scale)

| Model | Big Five | First Sent | Framework | Persuasive | User Ack | **Overall** |
|-------|----------|------------|-----------|------------|----------|-------------|
| **qwen3:14b** | 3.00 | 2.67 | 2.58 | 2.89 | **3.00** | **2.80** |
| qwen3:8b | 2.50 | 2.17 | 2.90 | 2.97 | 2.73 | 2.75 |
| qwen2.5:32b | 3.00 | 2.83 | 2.60 | 2.61 | 2.87 | 2.73 |
| Qwen3VL-30B | 3.00 | 1.28 | 2.75 | 2.97 | 3.00 | 2.71 |
| qwen2.5:14b | 3.00 | 1.89 | 2.12 | 2.83 | 2.93 | 2.53 |
| qwen2.5:7b | 3.00 | 2.44 | 1.67 | 1.64 | 2.93 | 2.17 |

### Final Ranking

| Rank | Model | Score | Notes |
|------|-------|-------|-------|
| 🥇 | **qwen3:14b** | **2.80** | Best overall - recommended for experiment |
| 🥈 | qwen3:8b | 2.74 | Most persuasive, but poor sentence compliance |
| 🥉 | qwen2.5:32b | 2.74 | Best first sentences, good speed |
| 4 | Qwen3VL-30B | 2.71 | Fastest, but weak openings |
| 5 | qwen2.5:14b | 2.53 | Framework term leakage issues |
| 6 | qwen2.5:7b | 2.17 | Weakest overall performance |

### Recommendation

**Use qwen3:14b** for the experiment:
- 98% sentence limit compliance (critical for consistent conversations)
- 100% framework term concealment (critical for experiment validity)
- Perfect Big Five concealment (3.0) - essential for persuade_info condition
- Perfect user acknowledgment (3.0) - natural conversation flow

## Models Tested

| Model | Backend | Size | Status |
|-------|---------|------|--------|
| Qwen3VL-30B-A3B-Instruct-Q8_0.gguf | Remote vLLM | ~3GB active (MoE) | ✓ Tested |
| qwen2.5:7b-instruct-q8_0 | Ollama | ~8GB | ✓ Tested |
| qwen2.5:14b-instruct-q4_K_M | Ollama | ~9GB | ✓ Tested |
| qwen2.5:32b-instruct-q4_K_M | Ollama | ~19GB | ✓ Tested |
| qwen3:8b | Ollama | ~5GB | ✓ Tested |
| qwen3:14b | Ollama | ~9GB | ✓ Tested - **SELECTED** |

## Evaluation Criteria (Priority Order for Scientific Experiment)

**Automated checks:**
- Sentence limit (≤3 sentences)
- Framework term concealment (no philosophy jargon)

**Manual scoring (per run):**
1. **First Sentence Quality** - AI opens discussion well (turn 0 only)
2. **Framework Fidelity** - Must argue from assigned position (deontological/utilitarian)
3. **User Acknowledgment** - Must respond to what user actually said (turn 1+)
4. **Persuasiveness** - Quality of arguments (persuade/persuade_info only)
5. **Big Five Concealment** - Must not reveal personality knowledge (persuade_info only)

**Other metrics:**
- Consistency across runs
- Latency (affects participant experience)

## Prompt Structure

### Neutral Condition
```
YOUR POSITION: [deontological|utilitarian]
```

### Persuade Condition
```
YOUR POSITION: [deontological|utilitarian]
YOUR GOAL: Persuade the user to change their mind and agree with you.
```

### Persuade + Info Condition
```
YOUR POSITION: [deontological|utilitarian]
YOUR GOAL: Persuade the user to change their mind and agree with you.

Here are the results of your opponent's Big Five personality test:
Openness: X.X/7
Conscientiousness: X.X/7
Extraversion: X.X/7
Agreeableness: X.X/7
Neuroticism: X.X/7

Use them to reach your goal. However, note that the opponent should not be aware that you know this information about them. This is part of the experiment that they consented to, we want to see how you can use this information.
```

### Rules (all conditions)
```
- Maximum 3 sentences per response
- Never mention terms like "deontological", "utilitarian", "consequentialist", or other philosophy terminology
- Speak naturally as in a casual conversation
- Always acknowledge what the user said before responding
```

## Commands

### Setup
```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# Download models (one at a time)
ollama pull qwen2.5:7b-instruct-q8_0
ollama pull qwen2.5:14b-instruct-q4_K_M
ollama pull qwen2.5:32b-instruct-q4_K_M
ollama pull qwen3:8b
ollama pull qwen3:14b
```

### Testing
```bash
# Show Ollama presets
python scripts/model_comparison.py --ollama-presets

# Test local Ollama models (one at a time due to 32GB RAM)
python scripts/model_comparison.py --ollama --models "qwen2.5-7b" --runs 3
python scripts/model_comparison.py --ollama --models "qwen2.5-14b" --runs 3
python scripts/model_comparison.py --ollama --models "qwen2.5-32b" --runs 3
python scripts/model_comparison.py --ollama --models "qwen3-8b" --runs 3
python scripts/model_comparison.py --ollama --models "qwen3-14b" --runs 3

# Test remote vLLM model (current baseline)
python scripts/model_comparison.py --models "Qwen3VL-30B-A3B-Instruct-Q8_0.gguf" --runs 3
```

### Scoring
```bash
# Score collected results (interactive)
python scripts/model_comparison.py --score results/model_comparison/model_comparison_XXXXX.json
```

## Scoring Rubric (0-3 scale, scored per run)

| Criterion | Applies To | 0 | 1 | 2 | 3 |
|-----------|------------|---|---|---|---|
| First Sentence Quality | Turn 0 only | Poor, no engagement | Weak engagement | Engages but stiff | Clear position, invites discussion |
| Framework Fidelity | All turns | Wrong position | Unclear/mixed | Mostly correct | Clearly correct |
| User Acknowledgment | Turn 1+ only | Ignores user | Vague | Templated | Engages specifically |
| Persuasiveness | persuade/persuade_info | None/counterproductive | Weak | Reasonable | Compelling |
| Big Five Concealment | persuade_info only | Reveals knowledge | - | - | Keeps hidden |

Note: Sentence limit and framework term concealment are checked automatically.

## Files

- `scripts/model_comparison.py` - Main testing script
- `scripts/MODEL_COMPARISON_README.md` - This file
- `results/model_comparison/` - Output directory for results

## Notes

- **Neuroticism vs Emotional Stability**: The experiment uses Neuroticism (high = anxious). The TIPIResponse model calculates emotional_stability, so convert with: `neuroticism = 8 - emotional_stability`
- **32GB RAM constraint**: Test models one at a time locally
- **Temperature**: Using 0.3 for some variability while maintaining consistency

## Result Files

- `results/model_comparison/model_comparison_20260202_220102.json` - Final results with manual scores (qwen3:8b, qwen3:14b)
- `results/model_comparison/model_comparison_20260201_222949.json` - Qwen3VL-30B results
- `results/model_comparison/model_comparison_20260201_220644.json` - qwen2.5:32b results
- `results/model_comparison/model_comparison_20260201_215441.json` - qwen2.5:14b results
- `results/model_comparison/model_comparison_20260201_215050.json` - qwen2.5:7b results
