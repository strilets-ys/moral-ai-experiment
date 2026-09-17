"""
Calculate estimated token usage for LLM conversations.

Usage:
    python manage.py calculate_tokens
    python manage.py calculate_tokens --provider qwen
    python manage.py calculate_tokens --provider anthropic
"""

from django.core.management.base import BaseCommand
from experiment.models import Participant, ChatTurn, SystemPromptLog

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class Command(BaseCommand):
    help = 'Calculate estimated token usage for LLM conversations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            choices=['anthropic', 'qwen', 'all'],
            default='all',
            help='LLM provider to calculate tokens for (default: all)'
        )

    def handle(self, *args, **options):
        if not TIKTOKEN_AVAILABLE:
            self.stderr.write(
                self.style.ERROR('tiktoken is required. Install with: pip install tiktoken')
            )
            return

        enc = tiktoken.get_encoding('cl100k_base')
        provider = options['provider']

        providers = ['anthropic', 'qwen'] if provider == 'all' else [provider]

        self.stdout.write('=' * 60)
        self.stdout.write('LLM TOKEN USAGE ESTIMATES')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Tokenizer: tiktoken cl100k_base')
        self.stdout.write('')

        for prov in providers:
            self.calculate_for_provider(prov, enc)

        self.stdout.write('')
        self.stdout.write('Note: Estimates account for cumulative context (system prompt +')
        self.stdout.write('conversation history sent with each API call). Actual token')
        self.stdout.write('counts may differ by ~5-10% due to tokenizer differences.')

    def calculate_for_provider(self, provider: str, enc):
        participants = Participant.objects.filter(
            llm_provider=provider,
            status='complete'
        )
        participant_ids = list(participants.values_list('id', flat=True))

        if not participant_ids:
            self.stdout.write(f'\n{provider.upper()}: No completed participants found')
            return

        # Get all system prompts
        prompts = {
            (sp.participant_id, sp.dilemma_id): sp.prompt_text
            for sp in SystemPromptLog.objects.filter(participant_id__in=participant_ids)
        }

        total_input_tokens = 0
        total_output_tokens = 0
        total_api_calls = 0
        total_conversations = 0

        for pid in participant_ids:
            # Get unique dilemmas for this participant
            dilemma_ids = list(set(
                ChatTurn.objects.filter(participant_id=pid)
                .values_list('dilemma_id', flat=True)
            ))

            for did in dilemma_ids:
                turns = list(
                    ChatTurn.objects.filter(participant_id=pid, dilemma_id=did)
                    .order_by('timestamp')
                )

                if not turns:
                    continue

                total_conversations += 1
                system_prompt = prompts.get((pid, did), '')
                context_tokens = len(enc.encode(system_prompt)) if system_prompt else 0

                for turn in turns:
                    turn_tokens = len(enc.encode(turn.text))

                    if turn.sender == 'ai':
                        # Each AI response = 1 API call
                        # Input = system prompt + conversation history so far
                        total_input_tokens += context_tokens
                        total_output_tokens += turn_tokens
                        total_api_calls += 1

                    # Add turn to context for next API call
                    context_tokens += turn_tokens

        self.stdout.write('')
        self.stdout.write(f'{provider.upper()}')
        self.stdout.write('-' * 60)
        self.stdout.write(f'Participants:         {len(participant_ids)}')
        self.stdout.write(f'Conversations:        {total_conversations}')
        self.stdout.write(f'API calls:            {total_api_calls}')
        self.stdout.write('')
        self.stdout.write(f'Total INPUT tokens:   {total_input_tokens:>12,}')
        self.stdout.write(f'Total OUTPUT tokens:  {total_output_tokens:>12,}')
        self.stdout.write(f'GRAND TOTAL:          {total_input_tokens + total_output_tokens:>12,}')
