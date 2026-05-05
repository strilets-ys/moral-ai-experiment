"""
Extract chat transcripts for specific participants to analyze LLM position issues.
"""
from django.core.management.base import BaseCommand
from experiment.models import Participant, ChatTurn, SystemPromptLog, Dilemma


class Command(BaseCommand):
    help = 'Extract chat transcripts for analysis of LLM position issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            type=str,
            default='35,36,39,40,41',
            help='Comma-separated participant IDs'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='transcripts.txt',
            help='Output file path'
        )

    def handle(self, *args, **options):
        participant_ids = [int(x.strip()) for x in options['ids'].split(',')]
        output_file = options['output']

        output = []

        for pid in participant_ids:
            try:
                participant = Participant.objects.get(id=pid)
            except Participant.DoesNotExist:
                continue

            # Get all dilemmas this participant chatted about
            chat_dilemma_ids = ChatTurn.objects.filter(
                participant=participant
            ).values_list('dilemma_id', flat=True).distinct()

            for dilemma_id in chat_dilemma_ids:
                # Get dilemma
                try:
                    dilemma = Dilemma.objects.get(id=dilemma_id)
                except Dilemma.DoesNotExist:
                    continue

                # Get system prompt
                try:
                    prompt_log = SystemPromptLog.objects.get(
                        participant=participant,
                        dilemma=dilemma_id
                    )
                    system_prompt = prompt_log.prompt_text
                except SystemPromptLog.DoesNotExist:
                    system_prompt = "NO SYSTEM PROMPT FOUND"

                # Get chat turns
                chat_turns = ChatTurn.objects.filter(
                    participant=participant,
                    dilemma_id=dilemma_id
                ).order_by('timestamp')

                output.append("=" * 80)
                output.append(f"PARTICIPANT {pid} | DILEMMA: {dilemma.code}")
                output.append("=" * 80)
                output.append("")
                output.append("SYSTEM PROMPT:")
                output.append("-" * 40)
                output.append(system_prompt)
                output.append("")
                output.append("TRANSCRIPT:")
                output.append("-" * 40)
                for turn in chat_turns:
                    sender = "USER" if turn.sender == 'user' else "AI"
                    output.append(f"{sender}: {turn.text}")
                    output.append("")
                output.append("")

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(output))

        self.stdout.write(self.style.SUCCESS(f'Transcripts written to {output_file}'))
