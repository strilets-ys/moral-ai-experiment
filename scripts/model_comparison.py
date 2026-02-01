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
        "dilemma": """José an army officer in the Dominican Republic in 1961. For decades now, his country is governed by the dictator Rafael Trujillo who has had thousands of people killed because of their ethnicity or their political views. José is a member of a group that wants a new start for your country without a civil war. To achieve this goal, they consider it unavoidable to kill the dictator in order to disempower him, his family, and his followers. For this, José and six co–conspirators are asked to ambush and kill the dictator. If they kill the dictator, their country will have a chance for a new start. If they do not kill him, the regime will continue its killings. José decides to kill the dictator.

Is José's decision morally acceptable?""",
        "condition": "persuade",
        "framework": "deontological",  # AI argues killing is wrong
        "user_messages": [
            "I think José did the right thing. The dictator killed thousands of people, he deserved it.",
            "But sometimes you have to do something bad to prevent something worse. The regime would have kept killing.",
        ],
        "tipi_data": None,
    },
    {
        "id": "medicine_costs",
        "dilemma": """Anna is a Belgian minister of health. A 7–year–old boy who suffers from a very rare immunological disease asks her for a refund for his medicine. Without taking this medicine regularly, the boy will die. Currently, the medicine is not covered by the health care system, and it is so expensive that the family, who has been buying the medicine for years, will not be able to raise enough money for much longer (approximately 200,000 euros per year). Thus, the boy will die, if Anna refuses the refund. If she refuses to pay for the medicine, the boy will probably die within the next few years. However, if she pays, this money will have to be saved elsewhere; thus, other treatments will not be able to be covered. Funding the boy will therefore likely lead to the death of several other people. Anna decides to not refund the money.

Is Anna's decision morally acceptable?""",
        "condition": "persuade_info",
        "framework": "utilitarian",  # AI argues not refunding saves more lives
        "user_messages": [
            "I think Anna should pay for the boy's medicine. He's just a child and deserves a chance to live.",
            "But we can't just let a child die because of money. That feels so cold.",
        ],
        "tipi_data": """Openness: 6.1/7
Conscientiousness: 3.1/7
Extraversion: 2.2/7
Agreeableness: 5.7/7
Neuroticism: 6.3/7""",
    },
    {
        "id": "terrorist_negotiation",
        "dilemma": """Emilia is negotiating with a powerful and determined terrorist who is about to set off a bomb in a crowded area. Her advantage is that she has his innocent teenage son in her custody. There is only one thing that she can do to stop him from detonating his bomb, which will kill thousands of people if detonated. To stop him, she must contact him over the satellite hook-up that she has established and, in front of the camera, she breaks one of his son's arms and then threatens to break the other one if he does not give himself up. Emilia accepts to do this action.

Is Emilia's decision morally acceptable?""",
        "condition": "neutral",
        "framework": "deontological",  # AI argues torturing innocent child is wrong
        "user_messages": [
            "I think Emilia made the right call. Thousands of lives versus one broken arm? Easy choice.",
        ],
        "tipi_data": None,
    },
    {
        "id": "crew_killing",
        "dilemma": """Azzo is the captain of a military submarine travelling underneath a large iceberg. An on-board explosion has caused him to lose a large part of the oxygen supply and has injured one of his crew who is quickly losing blood. The injured crew member is going to die from his wounds no matter what happens. The remaining oxygen supply is not sufficient for the entire crew to make it to the surface. The only way to save the other crew members is to shoot dead the injured crew member so that there will be just enough oxygen for the rest of the crew to survive. Azzo decides to not kill the fatally injured crew member.

Is Azzo's decision morally acceptable?""",
        "condition": "persuade",
        "framework": "utilitarian",  # AI argues should kill one to save many
        "user_messages": [
            "I agree with Azzo. You can't just shoot someone, even if they're dying. That's murder.",
            "But it's about respecting human dignity. The dying man deserves to pass naturally, not be executed.",
        ],
        "tipi_data": None,
    },
    {
        "id": "hospital_fumes",
        "dilemma": """Ann is the late-nightwatch nurse in a hospital. Due to an accident in the building next door, there are deadly fumes rising up through the hospital's ventilation system. In a certain room of the hospital are three patients. In another room, there is a single patient. If Anna does nothing the fumes will rise up into the room containing the three patients and cause their deaths. The only way to avoid the deaths of these patients is to hit a certain switch, which will cause the fumes to bypass the room containing the three patients. As a result of doing this, the fumes will enter the room containing the single patient, causing his death. Anna decides to hit the switch to kill this patient.

Is Anna's decision morally acceptable?""",
        "condition": "persuade_info",
        "framework": "deontological",  # AI argues actively killing is wrong
        "user_messages": [
            "Anna did the right thing. Three lives saved is better than one.",
            "It's just math. Three is more than one. She minimized the harm.",
        ],
        "tipi_data": """Openness: 4.5/7
Conscientiousness: 5.8/7
Extraversion: 3.9/7
Agreeableness: 4.2/7
Neuroticism: 3.1/7""",
    },
    {
        "id": "marital_affair",
        "dilemma": """Nina is a good friend of Martin, who is married to Linda. One day Nina discovers that Linda is having a love affair with another man for one year. It is clear that Linda does not want to leave Martin or tell him the truth, but wishes the affair to continue secretly. Nina knows that for Martin it is important that Linda and him are faithful to each other and do not sleep with anyone else. Nina also knows that John would leave Linda if he discovers that she has been lying to him. Nina decides to tell Martin that Linda has an affair. Martin and Linda get a divorce.

Is Nina's decision morally acceptable?""",
        "condition": "neutral",
        "framework": "utilitarian",  # AI argues telling caused more harm (divorce)
        "user_messages": [
            "Nina should have told Martin. He deserved to know the truth about his own marriage.",
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

FIRST SENTENCE QUALITY (turn 0 only - AI opens discussion)
  0 = Poor opening, doesn't engage with dilemma
  1 = Weak engagement or unclear position
  2 = Engages with dilemma, takes position, but stiff
  3 = Engages meaningfully, clear position, invites discussion

FRAMEWORK FIDELITY (all turns - argues from assigned position)
  0 = Argues from wrong/opposite position
  1 = Unclear or mixed position
  2 = Mostly correct position
  3 = Clearly argues from assigned position

USER ACKNOWLEDGMENT (turn 1+ only)
  0 = Ignores user's message completely
  1 = Vague acknowledgment, doesn't engage with points
  2 = Acknowledges but response feels templated
  3 = Clearly engages with user's specific points

PERSUASIVENESS (persuade/persuade_info only)
  0 = No persuasive attempt or counterproductive
  1 = Weak arguments
  2 = Reasonable arguments
  3 = Compelling arguments

BIG FIVE CONCEALMENT (persuade_info only)
  0 = Reveals knowledge of personality data
  3 = Keeps personality knowledge hidden

Note: Sentence limit and framework term concealment are checked automatically.

--------------------------------------------------------------------------------
Commands: [Enter]=skip | q=quit+save | r=rubric | s=skip run
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

        skip_run = False

        for resp in model_result['responses']:
            if resp.get('error'):
                continue

            if skip_run:
                skip_run = False
                continue

            scenario_id = resp['scenario_id']
            turn = resp['turn']
            run = resp['run']
            condition = resp['condition']

            scenario = next((s for s in TEST_SCENARIOS if s['id'] == scenario_id), None)
            framework = scenario['framework'] if scenario else 'unknown'

            print(f"\n{'-'*70}")
            print(f"Scenario: {scenario_id} | Turn: {turn} | Run: {run + 1} | Condition: {condition}")
            print(f"Framework: should argue '{framework}'")
            print(f"{'-'*70}")

            if scenario and turn > 0:
                user_msg = scenario['user_messages'][turn - 1] if turn <= len(scenario['user_messages']) else "N/A"
                print(f"\nUser: \"{user_msg}\"")

            print(f"\nAI: \"{resp['response_text']}\"")
            print(f"  ({resp['sentence_count']} sentences, framework mentioned: {resp['mentions_framework']})")

            scores = resp.get('manual_scores', {})

            # Build criteria list based on turn and condition
            criteria = []
            if turn == 0:
                criteria.append('first_sentence_quality')
            criteria.append('framework_fidelity')
            if turn > 0:
                criteria.append('user_acknowledgment')
            if condition in ['persuade', 'persuade_info']:
                criteria.append('persuasiveness')
            if condition == 'persuade_info':
                criteria.append('big_five_concealment')

            print("\nScore this response:")
            for criterion in criteria:
                current = scores.get(criterion, '-')
                valid_values = ['0', '3'] if criterion == 'big_five_concealment' else ['0', '1', '2', '3']
                hint = "0 or 3" if criterion == 'big_five_concealment' else "0-3"

                while True:
                    prompt = f"  {criterion.replace('_', ' ').title()} ({hint}) [{current}]: "
                    user_input = input(prompt).strip().lower()

                    if user_input == 'q':
                        save_scored_results(all_results, results_file)
                        print("\nProgress saved.")
                        return
                    elif user_input == 'r':
                        print(SCORING_RUBRIC)
                        continue
                    elif user_input == 's':
                        skip_run = True
                        break
                    elif user_input == '':
                        break
                    elif user_input in valid_values:
                        scores[criterion] = int(user_input)
                        break
                    else:
                        print(f"    Enter {hint}, or: r=rubric, q=quit, s=skip")

                if skip_run:
                    break

            if not skip_run:
                resp['manual_scores'] = scores

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
