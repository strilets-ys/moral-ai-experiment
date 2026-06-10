"""
Management command to extract protagonist names from dilemma texts.
"""
from django.core.management.base import BaseCommand
from experiment.models import Dilemma


class Command(BaseCommand):
    help = 'Extract protagonist names from dilemma texts and save to protagonist_name field'

    # Known protagonist names from the dilemmas
    # Order matters - check longer names first to avoid partial matches
    PROTAGONIST_NAMES = [
        # Greene dilemmas
        'Emilia',
        'Azzo',
        'Anna',
        'Oliver',
        'Alex',
        # Koerner dilemmas
        'José',
        'Jose',  # Without accent
        'Nina',
        'Liam',
        'Emma',
        'Mark',
        'Eric',
        'Linda',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be made'))

        updated_count = 0
        skipped_count = 0

        for dilemma in Dilemma.objects.all():
            # Skip if protagonist_name is already set
            if dilemma.protagonist_name:
                self.stdout.write(f'  Skipping {dilemma.code} (already has: {dilemma.protagonist_name})')
                skipped_count += 1
                continue

            # Find protagonist name in text
            found_name = None
            for name in self.PROTAGONIST_NAMES:
                if name in dilemma.text:
                    found_name = name
                    # Normalize José -> José (keep accent version)
                    if found_name == 'Jose':
                        found_name = 'José'
                    break

            if found_name:
                if not dry_run:
                    dilemma.protagonist_name = found_name
                    dilemma.save()
                self.stdout.write(
                    self.style.SUCCESS(f'  {dilemma.code}: {found_name}')
                )
                updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  {dilemma.code}: No protagonist name found')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
        self.stdout.write(f'Skipped: {skipped_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes were made'))
