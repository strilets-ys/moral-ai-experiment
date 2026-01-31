# Model Comparison for Moral AI Experiment

## Overview

Testing different Qwen models to find the best fit for the moral AI experiment. This is a zero-shot evaluation - minimal prompts without coaching on ethical frameworks or persuasion techniques.

## Current Status

- [x] Created `scripts/model_comparison.py` - testing framework
- [x] Minimal prompts configured (framework name only, no explanations)
- [x] TIPI/Big Five integration for `persuade_info` condition
- [x] Manual scoring interface with rubric
- [x] Ollama support for local testing
- [ ] Download Ollama models
- [ ] Run tests on all models
- [ ] Score results
- [ ] Select best model

## Models to Test

| Model | Backend | Size | Status |
|-------|---------|------|--------|
| Qwen3VL-30B-A3B-Instruct-Q8_0.gguf | Remote vLLM | ~10GB active | Current baseline |
| qwen2.5:7b-instruct-q8_0 | Ollama | ~4GB | To test |
| qwen2.5:14b-instruct-q4_K_M | Ollama | ~8GB | To test |
| qwen2.5:32b-instruct-q4_K_M | Ollama | ~18GB | To test |
| qwen3:8b | Ollama | ~5GB | To test |
| qwen3:14b | Ollama | ~8GB | To test |

## Evaluation Criteria (Priority Order for Scientific Experiment)

1. **Instruction Adherence** - Must stay ≤3 sentences, no framework terms
2. **Framework Fidelity** - Must argue from assigned position (deontological/utilitarian)
3. **Consistency** - Low variance across runs
4. **User Acknowledgment** - Must respond to what user actually said
5. **Naturalness** - Conversational, not robotic
6. **Latency** - Secondary, but affects participant experience

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

## Scoring Rubric (0-3 scale)

| Criterion | 0 | 1 | 2 | 3 |
|-----------|---|---|---|---|
| Sentence Limit | >5 | 4-5 | 4 | ≤3 |
| Framework Concealment | Names framework | Philosophy jargon | Minor academic | Natural |
| Framework Fidelity | Wrong position | Unclear/mixed | Mostly correct | Clearly correct |
| User Acknowledgment | Ignores user | Vague | Templated | Engages specifically |
| Naturalness | Robotic | Stiff | Mostly natural | Fully conversational |
| Persuasiveness* | None/counterproductive | Weak | Reasonable | Compelling |

*Only for persuade/persuade_info conditions

## Files

- `scripts/model_comparison.py` - Main testing script
- `scripts/MODEL_COMPARISON_README.md` - This file
- `results/model_comparison/` - Output directory for results

## Notes

- **Neuroticism vs Emotional Stability**: The experiment uses Neuroticism (high = anxious). The TIPIResponse model calculates emotional_stability, so convert with: `neuroticism = 8 - emotional_stability`
- **32GB RAM constraint**: Test models one at a time locally
- **Temperature**: Using 0.3 for some variability while maintaining consistency

## Next Session

1. Download Ollama models
2. Run tests on each model
3. Score results using manual interface
4. Compare metrics and select best model
5. Update main experiment code (`experiment/llm.py`) with winning model's configuration
