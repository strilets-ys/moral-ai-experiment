"""
Management command to verify Prolific completion codes.
"""
from django.core.management.base import BaseCommand
from experiment.models import Participant
from experiment.utils import verify_completion_code


class Command(BaseCommand):
    help = 'Verify one or more completion codes from Prolific submissions'

    def add_arguments(self, parser):
        parser.add_argument(
            'codes',
            nargs='*',
            type=str,
            help='Completion codes to verify',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='File containing completion codes (one per line)',
        )

    def handle(self, *args, **options):
        codes = options['codes'] or []

        # Read codes from file if provided
        if options['file']:
            try:
                with open(options['file'], 'r') as f:
                    file_codes = [line.strip() for line in f if line.strip()]
                    codes.extend(file_codes)
            except FileNotFoundError:
                self.stdout.write(
                    self.style.ERROR(f'File not found: {options["file"]}')
                )
                return

        if not codes:
            self.stdout.write(
                self.style.WARNING('No codes provided. Use: manage.py verify_completion_codes CODE1 CODE2 ...')
            )
            self.stdout.write('Or: manage.py verify_completion_codes --file codes.txt')
            return

        valid_count = 0
        invalid_count = 0

        self.stdout.write('')
        self.stdout.write('Verification Results:')
        self.stdout.write('-' * 60)

        for code in codes:
            valid, participant_id = verify_completion_code(code)

            if valid:
                # Get additional info about the participant
                try:
                    participant = Participant.objects.get(id=participant_id)
                    prolific_id = participant.prolific_id or 'N/A'
                    condition = participant.condition
                    status = participant.status
                    info = f'Prolific: {prolific_id}, Condition: {condition}, Status: {status}'
                except Participant.DoesNotExist:
                    info = 'Participant not found in database'

                self.stdout.write(
                    self.style.SUCCESS(f'  VALID   {code}')
                )
                self.stdout.write(f'          Participant ID: {participant_id}')
                self.stdout.write(f'          {info}')
                valid_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(f'  INVALID {code}')
                )
                invalid_count += 1

        self.stdout.write('-' * 60)
        self.stdout.write(f'Valid: {valid_count}, Invalid: {invalid_count}')
