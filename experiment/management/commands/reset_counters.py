"""
Management command to reset assignment counters before production data collection.
Keeps participant data intact but resets balancing counters.
"""
from django.core.management.base import BaseCommand

from experiment.models import StanceCombination, CompletionCell, AppSetting


RESET_FLAG_KEY = 'counters_reset_for_production'


class Command(BaseCommand):
    help = 'Reset assignment counters before production data collection (keeps participant data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Only run if not already run (for automated deploys)',
        )

    def handle(self, *args, **options):
        # Check if already run (when using --once)
        if options['once']:
            if AppSetting.get(RESET_FLAG_KEY):
                self.stdout.write('Counters already reset for production. Skipping.')
                return

        # Show current counter states
        self.stdout.write('Current counter states:')

        stance_combos = StanceCombination.objects.all()
        for combo in stance_combos:
            self.stdout.write(f'  StanceCombination {combo.combination_index}: usage_count={combo.usage_count}')

        completion_cells = CompletionCell.objects.all()
        for cell in completion_cells:
            self.stdout.write(f'  CompletionCell {cell.condition}/{cell.llm_provider}: completion_count={cell.completion_count}')

        if not options['yes']:
            self.stdout.write('\n' + self.style.WARNING(
                'This will RESET all assignment counters to 0.'
            ))
            confirm = input('Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return

        # Reset stance combination counters
        updated_stance = StanceCombination.objects.update(usage_count=0)
        self.stdout.write(f'Reset {updated_stance} stance combination counter(s).')

        # Reset completion cell counters
        updated_cells = CompletionCell.objects.update(completion_count=0)
        self.stdout.write(f'Reset {updated_cells} completion cell counter(s).')

        # Set flag so --once knows not to run again
        AppSetting.set(RESET_FLAG_KEY, 'true')

        self.stdout.write(self.style.SUCCESS('\nCounters reset. Ready for production data collection.'))
