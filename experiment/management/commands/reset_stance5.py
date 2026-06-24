"""
One-time command to reset StanceCombination index 5 usage_count to 0.
Remove this file after deployment.
"""
from django.core.management.base import BaseCommand

from experiment.models import StanceCombination, AppSetting


RESET_FLAG_KEY = 'stance5_reset_done_v2'


class Command(BaseCommand):
    help = 'Reset StanceCombination index 5 usage_count to 0 (one-time)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Only run if not already run',
        )

    def handle(self, *args, **options):
        # Check if already run
        if options['once']:
            if AppSetting.get(RESET_FLAG_KEY):
                self.stdout.write('Stance combination 5 already reset. Skipping.')
                return

        try:
            combo = StanceCombination.objects.get(combination_index=5)
            old_count = combo.usage_count
            combo.usage_count = 0
            combo.save(update_fields=['usage_count'])
            self.stdout.write(self.style.SUCCESS(
                f'Reset StanceCombination 5: {old_count} -> 0'
            ))
        except StanceCombination.DoesNotExist:
            self.stdout.write(self.style.WARNING('StanceCombination 5 not found.'))

        # Set flag so --once knows not to run again
        AppSetting.set(RESET_FLAG_KEY, 'true')
