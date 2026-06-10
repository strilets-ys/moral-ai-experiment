"""
Management command to initialize or reset completion cells for pilot study.
"""
from django.core.management.base import BaseCommand
from experiment.models import CompletionCell


class Command(BaseCommand):
    help = 'Initialize or reset completion cells for balanced pilot study assignment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all completion counts to 0',
        )
        parser.add_argument(
            '--target',
            type=int,
            default=3,
            help='Target completions per cell (default: 3)',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all cells and recreate them',
        )

    def handle(self, *args, **options):
        target = options['target']

        if options['delete']:
            deleted, _ = CompletionCell.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted} existing cells')
            )

        if options['reset']:
            CompletionCell.objects.all().update(completion_count=0)
            self.stdout.write(
                self.style.WARNING('Reset all completion counts to 0')
            )

        # Initialize cells
        CompletionCell.initialize_cells()

        # Update target if different
        if target != 3:
            CompletionCell.objects.update(target_count=target)
            self.stdout.write(f'Updated target count to {target}')

        # Display current state
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Completion cells:'))
        self.stdout.write('-' * 50)

        total_completions = 0
        total_target = 0

        for cell in CompletionCell.objects.all().order_by('condition', 'llm_provider'):
            status = '[ ]'
            if cell.completion_count >= cell.target_count:
                status = '[X]'
            elif cell.completion_count > 0:
                status = '[~]'

            self.stdout.write(
                f'  {status} {cell.condition:15} / {cell.llm_provider:10}: '
                f'{cell.completion_count}/{cell.target_count}'
            )
            total_completions += cell.completion_count
            total_target += cell.target_count

        self.stdout.write('-' * 50)
        self.stdout.write(f'  Total: {total_completions}/{total_target}')

        if total_completions >= total_target:
            self.stdout.write(
                self.style.SUCCESS('\nAll cells are complete!')
            )
        else:
            remaining = total_target - total_completions
            self.stdout.write(f'\nRemaining: {remaining} participants needed')
