import json
from datetime import datetime
from django.core.management.base import BaseCommand
from experiment.models import Dilemma
from experiment.llm import get_llm_client, build_system_prompt


class Command(BaseCommand):
    help = 'Test LLM first message generation for all dilemmas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            default='qwen',
            choices=['openai', 'anthropic', 'qwen'],
            help='LLM provider to use (default: qwen)',
        )
        parser.add_argument(
            '--condition',
            type=str,
            default='neutral',
            choices=['neutral', 'persuade', 'persuade_info'],
            help='Experimental condition (default: neutral)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='dilemma_test_results.json',
            help='Output file path (default: dilemma_test_results.json)',
        )
        parser.add_argument(
            '--dilemmas',
            type=str,
            nargs='+',
            help='Specific dilemma codes to test (e.g., Abduction_bg_prescription)',
        )
        parser.add_argument(
            '--positions',
            type=str,
            nargs='+',
            choices=['pro', 'contra'],
            help='Specific positions to test (default: both)',
        )
        parser.add_argument(
            '--runs',
            type=int,
            default=1,
            help='Number of times to run each test (default: 1)',
        )

    def handle(self, *args, **options):
        provider = options['provider']
        condition = options['condition']
        output_file = options['output']
        specific_dilemmas = options.get('dilemmas')
        specific_positions = options.get('positions') or ['pro', 'contra']
        num_runs = options.get('runs', 1)

        self.stdout.write(f'Testing with provider: {provider}, condition: {condition}, runs: {num_runs}')

        # Get LLM client
        try:
            client = get_llm_client(provider)
            self.stdout.write(self.style.SUCCESS('LLM client initialized'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize LLM client: {e}'))
            return

        # Get dilemmas
        if specific_dilemmas:
            dilemmas = Dilemma.objects.filter(code__in=specific_dilemmas).order_by('code')
            self.stdout.write(f'Testing specific dilemmas: {specific_dilemmas}')
        else:
            dilemmas = Dilemma.objects.all().order_by('code')
        self.stdout.write(f'Found {dilemmas.count()} dilemmas')

        results = []

        for dilemma in dilemmas:
            self.stdout.write(f'\nProcessing: {dilemma.code}')

            # Test specified positions for each dilemma
            for llm_position in specific_positions:
                # Determine framework based on position and low_rating_framework
                # If low_rating_framework is deontological:
                #   - contra (action wrong) = deontological
                #   - pro (action acceptable) = utilitarian
                # If low_rating_framework is utilitarian:
                #   - contra (action wrong) = utilitarian
                #   - pro (action acceptable) = deontological

                if dilemma.low_rating_framework == 'deontological':
                    if llm_position == 'contra':
                        llm_framework = 'deontological'
                    else:
                        llm_framework = 'utilitarian'
                else:  # low_rating_framework == 'utilitarian'
                    if llm_position == 'contra':
                        llm_framework = 'utilitarian'
                    else:
                        llm_framework = 'deontological'

                # Get position description if available
                if llm_framework == 'deontological':
                    position_description = dilemma.deontological_position or None
                else:
                    position_description = dilemma.utilitarian_position or None

                # Build system prompt
                system_prompt = build_system_prompt(
                    condition=condition,
                    dilemma_text=dilemma.text,
                    llm_framework=llm_framework,
                    llm_position=llm_position,
                    stance_mode='opposite',  # doesn't matter for neutral, but needed
                    participant_rating=None,
                    personality_profile=None,
                    position_description=position_description,
                )

                # Run multiple times if requested
                for run_num in range(1, num_runs + 1):
                    # Generate first message (empty messages = AI initiates)
                    try:
                        first_message = client.get_response(
                            system_prompt=system_prompt,
                            messages=[]
                        )
                        error = None
                    except Exception as e:
                        first_message = None
                        error = str(e)

                    result = {
                        'dilemma_code': dilemma.code,
                        'dilemma_category': dilemma.category,
                        'dilemma_author': dilemma.author,
                        'low_rating_framework': dilemma.low_rating_framework,
                        'llm_framework': llm_framework,
                        'llm_position': llm_position,
                        'expected_stance': 'Action IS acceptable' if llm_position == 'pro' else 'Action is WRONG',
                        'run_number': run_num,
                        'system_prompt': system_prompt,
                        'first_message': first_message,
                        'error': error,
                        'correct': None,  # To be filled manually
                        'notes': '',  # For manual notes
                    }
                    results.append(result)

                    status = 'OK' if first_message else f'ERROR: {error}'
                    run_label = f' (run {run_num})' if num_runs > 1 else ''
                    self.stdout.write(f'  {llm_position} ({llm_framework}){run_label}: {status}')

        # Save results to JSON file
        output_data = {
            'metadata': {
                'provider': provider,
                'condition': condition,
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(results),
            },
            'results': results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        # Also create a readable markdown file for manual review
        md_file = output_file.replace('.json', '.md')
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f'# Dilemma Test Results\n\n')
            f.write(f'**Provider:** {provider}  \n')
            f.write(f'**Condition:** {condition}  \n')
            f.write(f'**Timestamp:** {datetime.now().isoformat()}  \n')
            f.write(f'**Total tests:** {len(results)}\n\n')
            f.write('---\n\n')
            f.write('## How to review\n')
            f.write('For each test, check if the LLM message matches the expected stance.\n')
            f.write('- Mark `[ ]` as `[x]` if CORRECT\n')
            f.write('- Mark `[ ]` as `[!]` if INCORRECT\n\n')
            f.write('---\n\n')

            current_dilemma = None
            for i, result in enumerate(results, 1):
                if result['dilemma_code'] != current_dilemma:
                    current_dilemma = result['dilemma_code']
                    f.write(f'## {result["dilemma_code"]}\n')
                    f.write(f'**Category:** {result["dilemma_category"]} | **Author:** {result["dilemma_author"]}\n\n')

                run_label = f' (Run {result.get("run_number", 1)})' if result.get("run_number", 1) > 1 or num_runs > 1 else ''
                f.write(f'### Test {i}: {result["llm_position"].upper()} position{run_label}\n\n')
                f.write(f'**Framework:** {result["llm_framework"]}  \n')
                f.write(f'**Expected:** {result["expected_stance"]}  \n\n')
                f.write(f'**LLM Message:**\n')
                if result['first_message']:
                    f.write(f'> {result["first_message"]}\n\n')
                else:
                    f.write(f'> ERROR: {result["error"]}\n\n')
                f.write(f'- [ ] Correct\n\n')
                f.write('---\n\n')

        self.stdout.write(self.style.SUCCESS(f'\nResults saved to:'))
        self.stdout.write(f'  - {output_file} (JSON for data)')
        self.stdout.write(f'  - {md_file} (Markdown for review)')
        self.stdout.write(f'\nTotal tests: {len(results)}')
