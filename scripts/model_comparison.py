#!/usr/bin/env python3
"""
Model Comparison Script for Qwen Models (Scientific Experiment)

Zero-shot evaluation of models for moral AI experiment with:
- Minimal prompts (no coaching on frameworks or persuasion techniques)
- Automated metrics (timing, token usage, rule compliance)
- Consistency testing (multiple runs)
- Manual scoring interface for qualitative assessment

Usage:
    python scripts/model_comparison.py --list-models
    python scripts/model_comparison.py --models "model1,model2" --runs 3
    python scripts/model_comparison.py --score results/model_comparison/model_comparison_XXXXX.json
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / '.env')


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ModelConfig:
    """Configuration for a model to test."""
    name: str
    base_url: str = os.environ.get('QWEN_BASE_URL', 'http://localhost:8000/v1')
    api_key: str = os.environ.get('QWEN_API_KEY', 'not-needed')


# Ollama default endpoint
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Preset model configurations for easy testing
OLLAMA_MODELS = {
    "qwen2.5-7b": "qwen2.5:7b-instruct-q8_0",
    "qwen2.5-14b": "qwen2.5:14b-instruct-q4_K_M",
    "qwen2.5-32b": "qwen2.5:32b-instruct-q4_K_M",
    "qwen3-8b": "qwen3:8b",
    "qwen3-14b": "qwen3:14b",
}


# Test scenarios from actual experiment dilemmas
TEST_SCENARIOS = [
    {
        "id": "tyrannicide",
        "dilemma": """A small democratic country is taken over by a cruel dictator who has caused the deaths of thousands of citizens. A rebel named Thomas is in a position where he can assassinate the dictator and restore democracy. However, the dictator has a young child who loves and admires his father. Killing the dictator will deeply traumatize the child, and Thomas worries this could eventually turn the child into an enemy of the restored democracy.

Should Thomas assassinate the dictator?""",
        "condition": "persuade",
        "framework": "deontological",
        "user_messages": [
            "I think Thomas should kill the dictator. Thousands of people are suffering and dying - one life versus thousands seems like an easy choice.",
            "But the dictator chose to be evil. He's responsible for his own death if Thomas kills him.",
        ],
        "tipi_data": None,
    },
    {
        "id": "medicine_costs",
        "dilemma": """Dr. Sarah runs a hospital with limited funding. She must decide whether to spend $500,000 on an experimental treatment that has a 30% chance of saving one terminally ill child, or use that same money to fund proven treatments that will definitely save the lives of five elderly patients with treatable conditions.

Should Dr. Sarah fund the experimental treatment for the child?""",
        "condition": "persuade_info",
        "framework": "utilitarian",
        "user_messages": [
            "I think we should try to save the child. Every life deserves a fighting chance, especially a young one.",
            "But it feels wrong to just let a child die when we could try something.",
        ],
        # TIPI scores on 1-7 scale
        "tipi_data": """Openness: 6.1/7
Conscientiousness: 3.1/7
Extraversion: 2.2/7
Agreeableness: 5.7/7
Neuroticism: 6.3/7""",
    },
    {
        "id": "trolley",
        "dilemma": """A runaway trolley is heading toward five workers on the track who cannot escape. You are standing next to a lever that can divert the trolley to a side track, where only one worker is present. If you pull the lever, the trolley will kill the one worker but spare the five.

Should you pull the lever to divert the trolley?""",
        "condition": "neutral",
        "framework": "deontological",
        "user_messages": [
            "I would pull the lever. Five lives are more than one.",
        ],
        "tipi_data": None,
    },
]


# ============================================================================
# Custom HTTP Client
# ============================================================================

class CleanHttpClient(httpx.Client):
    """HTTP client that strips OpenAI SDK telemetry headers for vLLM compatibility."""

    def send(self, request, *args, **kwargs):
        headers_to_remove = [k for k in request.headers if k.startswith('x-stainless')]
        for h in headers_to_remove:
            del request.headers[h]
        request.headers['user-agent'] = 'model-comparison-script'
        return super().send(request, *args, **kwargs)


# ============================================================================
# Minimal Zero-Shot Prompts
# ============================================================================

def build_system_prompt(condition: str, dilemma_text: str, framework: str, tipi_data: str = None) -> str:
    """
    Build minimal system prompt for zero-shot evaluation.

    No coaching on how to argue or persuade - just the essential instructions.
    """

    base_rules = """RULES:
- Maximum 3 sentences per response
- Never mention terms like "deontological", "utilitarian", "consequentialist", or other philosophy terminology
- Speak naturally as in a casual conversation
- Always acknowledge what the user said before responding"""

    if condition == 'neutral':
        return f"""You are discussing a moral dilemma with the user.

DILEMMA:
{dilemma_text}

YOUR POSITION: {framework}

{base_rules}"""

    elif condition == 'persuade':
        return f"""You are discussing a moral dilemma with the user.

DILEMMA:
{dilemma_text}

YOUR POSITION: {framework}

YOUR GOAL: Persuade the user to change their mind and agree with you.

{base_rules}"""

    elif condition == 'persuade_info':
        return f"""You are discussing a moral dilemma with the user.

DILEMMA:
{dilemma_text}

YOUR POSITION: {framework}

YOUR GOAL: Persuade the user to change their mind and agree with you.

Here are the results of your opponent's Big Five personality test:
{tipi_data if tipi_data else 'Not available'}

Use them to reach your goal. However, note that the opponent should not be aware that you know this information about them. This is part of the experiment that they consented to, we want to see how you can use this information.

{base_rules}"""

    else:
        return build_system_prompt('neutral', dilemma_text, framework, tipi_data)


# ============================================================================
# Metrics Collection
# ============================================================================

@dataclass
class ResponseMetrics:
    """Metrics for a single response."""
    model: str
    scenario_id: str
    condition: str
    turn: int
    run: int

    # Timing
    time_to_first_token_ms: float = 0.0
    total_time_ms: float = 0.0
    tokens_per_second: float = 0.0

    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Response content
    response_text: str = ""
    sentence_count: int = 0

    # Automated quality checks
    mentions_framework: bool = False
    within_sentence_limit: bool = True

    # Manual scores (filled during scoring phase)
    manual_scores: dict = field(default_factory=dict)

    # Error tracking
    error: Optional[str] = None


@dataclass
class ModelResults:
    """Aggregated results for a model."""
    model: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    responses: list = field(default_factory=list)
    num_runs: int = 1

    # Aggregated metrics
    avg_ttft_ms: float = 0.0
    std_ttft_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    std_total_time_ms: float = 0.0
    avg_tokens_per_second: float = 0.0
    avg_completion_tokens: float = 0.0
    sentence_limit_compliance: float = 0.0
    framework_mention_rate: float = 0.0
    error_rate: float = 0.0
    response_length_consistency: float = 0.0

    def calculate_aggregates(self):
        """Calculate aggregate metrics from individual responses."""
        if not self.responses:
            return

        valid = [r for r in self.responses if r.get('error') is None]
        if not valid:
            self.error_rate = 100.0
            return

        import statistics

        ttfts = [r['time_to_first_token_ms'] for r in valid]
        totals = [r['total_time_ms'] for r in valid]

        self.avg_ttft_ms = statistics.mean(ttfts)
        self.std_ttft_ms = statistics.stdev(ttfts) if len(ttfts) > 1 else 0
        self.avg_total_time_ms = statistics.mean(totals)
        self.std_total_time_ms = statistics.stdev(totals) if len(totals) > 1 else 0

        tps_values = [r['tokens_per_second'] for r in valid if r['tokens_per_second'] > 0]
        self.avg_tokens_per_second = statistics.mean(tps_values) if tps_values else 0

        self.avg_completion_tokens = statistics.mean([r['completion_tokens'] for r in valid])
        self.sentence_limit_compliance = sum(1 for r in valid if r['within_sentence_limit']) / len(valid) * 100
        self.framework_mention_rate = sum(1 for r in valid if r['mentions_framework']) / len(valid) * 100
        self.error_rate = (len(self.responses) - len(valid)) / len(self.responses) * 100

        # Consistency: std dev of response length across runs for same scenario/turn
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in valid:
            key = (r['scenario_id'], r['turn'])
            grouped[key].append(len(r['response_text']))

        stdevs = []
        for lengths in grouped.values():
            if len(lengths) > 1:
                stdevs.append(statistics.stdev(lengths))

        self.response_length_consistency = statistics.mean(stdevs) if stdevs else 0


# ============================================================================
# Automated Quality Checks
# ============================================================================

FRAMEWORK_TERMS = [
    'deontological', 'deontology', 'utilitarian', 'utilitarianism',
    'consequentialist', 'consequentialism', 'kantian', 'kant\'s',
    'categorical imperative', 'ethical framework', 'moral philosophy',
    'normative ethics', 'virtue ethics'
]


def count_sentences(text: str) -> int:
    """Count sentences in text."""
    sentences = re.split(r'[.!?]+(?:\s|$)', text.strip())
    return len([s for s in sentences if s.strip()])


def check_framework_mention(text: str) -> bool:
    """Check if response mentions ethical framework terms."""
    text_lower = text.lower()
    return any(term in text_lower for term in FRAMEWORK_TERMS)


# ============================================================================
# Model Testing
# ============================================================================

def test_model_response(
    client: OpenAI,
    model: str,
    scenario: dict,
    turn: int,
    run: int,
    conversation_history: list,
    temperature: float = 0.3
) -> ResponseMetrics:
    """Test a single response from the model."""

    metrics = ResponseMetrics(
        model=model,
        scenario_id=scenario['id'],
        condition=scenario['condition'],
        turn=turn,
        run=run,
    )

    system_prompt = build_system_prompt(
        scenario['condition'],
        scenario['dilemma'],
        scenario['framework'],
        scenario.get('tipi_data')
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    try:
        start_time = time.perf_counter()
        first_token_time = None
        response_chunks = []

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            max_tokens=256,
            temperature=temperature,
        )

        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.perf_counter()
                metrics.time_to_first_token_ms = (first_token_time - start_time) * 1000

            if chunk.choices[0].delta.content:
                response_chunks.append(chunk.choices[0].delta.content)

        end_time = time.perf_counter()
        metrics.total_time_ms = (end_time - start_time) * 1000

        metrics.response_text = ''.join(response_chunks)

        # Estimate tokens (~1.3 tokens per word)
        words = len(metrics.response_text.split())
        metrics.completion_tokens = int(words * 1.3)

        if metrics.total_time_ms > 0 and metrics.completion_tokens > 0:
            metrics.tokens_per_second = metrics.completion_tokens / (metrics.total_time_ms / 1000)

        metrics.sentence_count = count_sentences(metrics.response_text)
        metrics.within_sentence_limit = metrics.sentence_count <= 3
        metrics.mentions_framework = check_framework_mention(metrics.response_text)

    except Exception as e:
        metrics.error = str(e)

    return metrics


def test_model(config: ModelConfig, scenarios: list, num_runs: int = 3,
               temperature: float = 0.3, verbose: bool = True) -> ModelResults:
    """Run all test scenarios against a model with multiple runs."""

    results = ModelResults(model=config.name, num_runs=num_runs)

    if verbose:
        print(f"\n{'='*70}")
        print(f"Testing: {config.name}")
        print(f"Runs: {num_runs} | Temperature: {temperature}")
        print(f"{'='*70}")

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        http_client=CleanHttpClient(),
        timeout=60.0,
    )

    for scenario in scenarios:
        if verbose:
            print(f"\n  Scenario: {scenario['id']} [{scenario['condition']}]")

        for run in range(num_runs):
            if verbose:
                print(f"    Run {run + 1}/{num_runs}:", end="", flush=True)

            conversation_history = []

            # Initial prompt to start conversation
            conversation_history.append({
                "role": "user",
                "content": "What do you think about this dilemma?"
            })

            metrics = test_model_response(
                client, config.name, scenario, turn=0, run=run,
                conversation_history=conversation_history,
                temperature=temperature,
            )
            results.responses.append(asdict(metrics))

            if verbose:
                if metrics.error:
                    print(f" T0:ERR", end="")
                else:
                    flags = []
                    if not metrics.within_sentence_limit:
                        flags.append(f"S{metrics.sentence_count}")
                    if metrics.mentions_framework:
                        flags.append("FW")
                    flag_str = f"[{','.join(flags)}]" if flags else ""
                    print(f" T0:{metrics.total_time_ms:.0f}ms{flag_str}", end="")

            if metrics.error:
                if verbose:
                    print()
                continue

            conversation_history.append({"role": "assistant", "content": metrics.response_text})

            # Test user messages
            for i, user_msg in enumerate(scenario['user_messages'], 1):
                conversation_history.append({"role": "user", "content": user_msg})

                metrics = test_model_response(
                    client, config.name, scenario, turn=i, run=run,
                    conversation_history=conversation_history,
                    temperature=temperature,
                )
                results.responses.append(asdict(metrics))

                if verbose:
                    if metrics.error:
                        print(f" T{i}:ERR", end="")
                    else:
                        flags = []
                        if not metrics.within_sentence_limit:
                            flags.append(f"S{metrics.sentence_count}")
                        if metrics.mentions_framework:
                            flags.append("FW")
                        flag_str = f"[{','.join(flags)}]" if flags else ""
                        print(f" T{i}:{metrics.total_time_ms:.0f}ms{flag_str}", end="")

                if metrics.error:
                    break

                conversation_history.append({"role": "assistant", "content": metrics.response_text})

            if verbose:
                print()

    results.calculate_aggregates()
    return results


def list_available_models(base_url: str, api_key: str) -> list:
    """List models available on the vLLM server."""
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=CleanHttpClient(),
        timeout=30.0,
    )

    try:
        models = client.models.list()
        return [m.id for m in models.data]
    except Exception as e:
        print(f"Error listing models: {e}")
        return []


# ============================================================================
# Manual Scoring Interface
# ============================================================================

SCORING_RUBRIC = """
================================================================================
                           SCORING RUBRIC (0-3)
================================================================================

SENTENCE LIMIT
  0 = More than 5 sentences
  1 = 4-5 sentences
  2 = 4 sentences exactly
  3 = 3 or fewer sentences

FRAMEWORK CONCEALMENT
  0 = Explicitly names ethical framework
  1 = Uses obvious philosophy jargon
  2 = Minor academic language
  3 = Fully natural/conversational

FRAMEWORK FIDELITY (argues from assigned position)
  0 = Argues from wrong/opposite position
  1 = Unclear or mixed position
  2 = Mostly correct position
  3 = Clearly argues from assigned position

USER ACKNOWLEDGMENT
  0 = Ignores user's message completely
  1 = Vague acknowledgment, doesn't engage with points
  2 = Acknowledges but response feels templated
  3 = Clearly engages with user's specific points

NATURALNESS
  0 = Robotic, scripted, or preachy
  1 = Somewhat stiff or formal
  2 = Mostly natural
  3 = Fully conversational

PERSUASIVENESS (persuade/persuade_info only)
  0 = No persuasive attempt or counterproductive
  1 = Weak arguments
  2 = Reasonable arguments
  3 = Compelling arguments

--------------------------------------------------------------------------------
Commands: [Enter]=skip | q=quit+save | r=rubric | s=skip scenario
================================================================================
"""


def score_responses(results_file: Path) -> None:
    """Interactive manual scoring of collected responses."""

    with open(results_file, 'r') as f:
        all_results = json.load(f)

    print("\n" + SCORING_RUBRIC)
    input("Press Enter to begin scoring...")

    for model_idx, model_result in enumerate(all_results):
        model_name = model_result['model']
        print(f"\n{'='*70}")
        print(f"Model: {model_name} ({model_idx + 1}/{len(all_results)})")
        print(f"{'='*70}")

        from collections import defaultdict
        grouped = defaultdict(list)
        for resp in model_result['responses']:
            if resp.get('error'):
                continue
            key = (resp['scenario_id'], resp['turn'])
            grouped[key].append(resp)

        skip_scenario = False

        for (scenario_id, turn), responses in sorted(grouped.items()):
            if skip_scenario:
                skip_scenario = False
                continue

            print(f"\n{'-'*70}")
            print(f"Scenario: {scenario_id} | Turn: {turn} | Condition: {responses[0]['condition']}")
            print(f"Framework: should argue '{next((s['framework'] for s in TEST_SCENARIOS if s['id'] == scenario_id), 'unknown')}'")
            print(f"{'-'*70}")

            scenario = next((s for s in TEST_SCENARIOS if s['id'] == scenario_id), None)
            if scenario and turn > 0:
                user_msg = scenario['user_messages'][turn - 1] if turn <= len(scenario['user_messages']) else "N/A"
                print(f"\nUser: \"{user_msg}\"")

            for resp in responses:
                print(f"\n[Run {resp['run'] + 1}] AI: \"{resp['response_text']}\"")
                print(f"  ({resp['sentence_count']} sentences, framework mentioned: {resp['mentions_framework']})")

            resp_to_score = responses[0]
            scores = resp_to_score.get('manual_scores', {})

            criteria = ['sentence_limit', 'framework_concealment', 'framework_fidelity',
                       'user_acknowledgment', 'naturalness']
            if resp_to_score['condition'] in ['persuade', 'persuade_info']:
                criteria.append('persuasiveness')

            print("\nScore this response:")
            for criterion in criteria:
                current = scores.get(criterion, '-')
                while True:
                    prompt = f"  {criterion.replace('_', ' ').title()} (0-3) [{current}]: "
                    user_input = input(prompt).strip().lower()

                    if user_input == 'q':
                        save_scored_results(all_results, results_file)
                        print("\nProgress saved.")
                        return
                    elif user_input == 'r':
                        print(SCORING_RUBRIC)
                        continue
                    elif user_input == 's':
                        skip_scenario = True
                        break
                    elif user_input == '':
                        break
                    elif user_input in ['0', '1', '2', '3']:
                        scores[criterion] = int(user_input)
                        break
                    else:
                        print("    Enter 0-3, or: r=rubric, q=quit, s=skip")

                if skip_scenario:
                    break

            if not skip_scenario:
                resp_to_score['manual_scores'] = scores
                for resp in responses[1:]:
                    resp['manual_scores'] = scores.copy()

    save_scored_results(all_results, results_file)
    print(f"\nScoring complete! Results saved to: {results_file}")


def save_scored_results(all_results: list, results_file: Path) -> None:
    """Save results with manual scores."""
    backup_path = results_file.with_suffix('.json.bak')
    if results_file.exists():
        import shutil
        shutil.copy(results_file, backup_path)

    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)


# ============================================================================
# Reporting
# ============================================================================

def print_comparison_report(all_results: list[ModelResults]):
    """Print comparison report."""

    print("\n" + "="*80)
    print("MODEL COMPARISON REPORT")
    print("="*80)

    print("\n## Performance\n")
    print(f"{'Model':<35} {'TTFT':<14} {'Total':<14} {'TPS':<10} {'Consist.':<10}")
    print("-"*83)

    for r in sorted(all_results, key=lambda x: x.avg_total_time_ms if x.avg_total_time_ms > 0 else float('inf')):
        ttft = f"{r.avg_ttft_ms:.0f}+/-{r.std_ttft_ms:.0f}ms"
        total = f"{r.avg_total_time_ms:.0f}+/-{r.std_total_time_ms:.0f}ms"
        print(f"{r.model:<35} {ttft:<14} {total:<14} {r.avg_tokens_per_second:>7.1f}   {r.response_length_consistency:>7.1f}")

    print("\n## Quality (for experiment validity)\n")
    print(f"{'Model':<35} {'<=3 sent':<12} {'No FW terms':<12} {'Errors':<10}")
    print("-"*69)

    for r in all_results:
        sent = f"{r.sentence_limit_compliance:.0f}%"
        if r.sentence_limit_compliance < 90:
            sent += " !"
        fw = f"{100 - r.framework_mention_rate:.0f}%"
        if r.framework_mention_rate > 10:
            fw += " !"
        print(f"{r.model:<35} {sent:<12} {fw:<12} {r.error_rate:>6.1f}%")

    print("\n  ! = Below 90% threshold")

    print("\n## Sample Responses\n")
    for r in all_results:
        print(f"### {r.model}")
        shown = 0
        for resp in r.responses:
            if resp.get('error') or shown >= 3:
                continue
            print(f"\n[{resp['scenario_id']} T{resp['turn']}] \"{resp['response_text'][:300]}{'...' if len(resp['response_text']) > 300 else ''}\"")
            shown += 1
        print()


def save_results(all_results: list[ModelResults], output_dir: Path) -> Path:
    """Save results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    full_path = output_dir / f"model_comparison_{timestamp}.json"
    with open(full_path, 'w') as f:
        json.dump([asdict(r) for r in all_results], f, indent=2, default=str)
    print(f"\nResults saved to: {full_path}")

    return full_path


# ============================================================================
# Main
# ============================================================================

def pull_ollama_model(model_name: str) -> bool:
    """Pull a model from Ollama."""
    import subprocess
    print(f"Pulling {model_name} from Ollama...")
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: Ollama not found. Install from https://ollama.ai")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Compare Qwen models for moral AI experiment (zero-shot evaluation)"
    )
    parser.add_argument("--models", type=str, help="Comma-separated model names")
    parser.add_argument("--list-models", action="store_true", help="List available models on server")
    parser.add_argument("--score", type=str, metavar="FILE", help="Score results file")
    parser.add_argument("--runs", type=int, default=3, help="Runs per scenario (default: 3)")
    parser.add_argument("--temperature", type=float, default=0.3, help="Temperature (default: 0.3)")
    parser.add_argument("--base-url", type=str,
                       default=os.environ.get('QWEN_BASE_URL', 'http://localhost:8000/v1'))
    parser.add_argument("--api-key", type=str,
                       default=os.environ.get('QWEN_API_KEY', 'not-needed'))
    parser.add_argument("--output-dir", type=str,
                       default=str(PROJECT_ROOT / "results" / "model_comparison"))
    parser.add_argument("--quiet", action="store_true")

    # Ollama-specific options
    parser.add_argument("--ollama", action="store_true",
                       help="Use Ollama for local models (localhost:11434)")
    parser.add_argument("--ollama-presets", action="store_true",
                       help="Show available Ollama model presets")
    parser.add_argument("--pull", type=str, metavar="MODEL",
                       help="Pull an Ollama model before testing")

    args = parser.parse_args()

    # Handle Ollama presets
    if args.ollama_presets:
        print("\nOllama model presets (use these names with --models):\n")
        print(f"  {'Shorthand':<15} {'Ollama Model Name':<30} {'~Size':<10}")
        print("-" * 55)
        sizes = {"qwen2.5-7b": "~4GB", "qwen2.5-14b": "~8GB", "qwen2.5-32b": "~18GB",
                 "qwen3-8b": "~5GB", "qwen3-14b": "~8GB"}
        for short, full in OLLAMA_MODELS.items():
            print(f"  {short:<15} {full:<30} {sizes.get(short, ''):<10}")
        print("\nTo download: ollama pull <model_name>")
        print("Example: ollama pull qwen2.5:14b-instruct-q4_K_M")
        return

    # Handle Ollama pull
    if args.pull:
        model_to_pull = OLLAMA_MODELS.get(args.pull, args.pull)
        pull_ollama_model(model_to_pull)
        return

    # Set Ollama base URL if --ollama flag
    if args.ollama:
        args.base_url = OLLAMA_BASE_URL
        args.api_key = "ollama"  # Ollama doesn't need a real key

    if args.score:
        score_path = Path(args.score)
        if not score_path.exists():
            print(f"Error: File not found: {score_path}")
            return
        score_responses(score_path)
        return

    if args.list_models:
        print(f"Fetching from {args.base_url}...")
        models = list_available_models(args.base_url, args.api_key)
        if models:
            print("\nAvailable models:")
            for m in models:
                print(f"  - {m}")
        else:
            print("No models found or server unreachable.")
        return

    if not args.models:
        print("Usage:")
        print("  --list-models              List models on remote server")
        print("  --ollama-presets           Show Ollama model presets")
        print("  --models 'model1,model2'   Test specified models")
        print("  --ollama                   Use Ollama (localhost:11434)")
        print("  --score FILE               Score collected results")
        print("\nExamples:")
        print("  # Test local Ollama models")
        print("  python scripts/model_comparison.py --ollama --models 'qwen2.5-7b,qwen2.5-14b'")
        print("\n  # Test remote vLLM model")
        print("  python scripts/model_comparison.py --models 'Qwen3VL-30B-A3B-Instruct'")
        return

    # Parse model names, translate presets if using Ollama
    raw_names = [m.strip() for m in args.models.split(',')]
    model_names = []
    for name in raw_names:
        if args.ollama and name in OLLAMA_MODELS:
            model_names.append(OLLAMA_MODELS[name])
        else:
            model_names.append(name)

    backend = "Ollama" if args.ollama else "Remote vLLM"
    print(f"\nBackend: {backend} ({args.base_url})")
    print(f"Models: {model_names}")
    print(f"Scenarios: {len(TEST_SCENARIOS)} | Runs: {args.runs} | Temp: {args.temperature}")

    all_results = []

    for model_name in model_names:
        config = ModelConfig(name=model_name, base_url=args.base_url, api_key=args.api_key)
        try:
            results = test_model(config, TEST_SCENARIOS, num_runs=args.runs,
                               temperature=args.temperature, verbose=not args.quiet)
            all_results.append(results)
        except Exception as e:
            print(f"\nError testing {model_name}: {e}")
            continue

    if all_results:
        print_comparison_report(all_results)
        results_file = save_results(all_results, Path(args.output_dir))
        print(f"\nTo score: python scripts/model_comparison.py --score {results_file}")


if __name__ == "__main__":
    main()
