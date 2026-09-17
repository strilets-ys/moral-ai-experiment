"""
Backup production database locally.

Usage:
    python manage.py backup_db --database-url="postgresql://..."

Or set DATABASE_URL in environment/`.env` file.
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv


class Command(BaseCommand):
    help = 'Backup production PostgreSQL database to local file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database-url',
            type=str,
            help='PostgreSQL connection URL (or set DATABASE_URL env var)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to store backups (default: backups/)',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=7,
            help='Number of backups to keep (default: 7, 0 = keep all)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['sql', 'custom', 'json'],
            default='custom',
            help='Backup format: sql (plain), custom (pg_dump -Fc), json (Django dumpdata)',
        )

    def handle(self, *args, **options):
        # Load .env file
        load_dotenv()

        # Get database URL
        database_url = options['database_url'] or os.environ.get('DATABASE_URL')
        if not database_url:
            raise CommandError(
                'No database URL provided. Use --database-url or set DATABASE_URL environment variable.'
            )

        # Parse the URL
        parsed = urlparse(database_url)
        if parsed.scheme not in ('postgres', 'postgresql'):
            raise CommandError(f'Only PostgreSQL is supported, got: {parsed.scheme}')

        # Create backup directory
        backup_dir = Path(options['output_dir'])
        backup_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_format = options['format']

        if backup_format == 'json':
            filename = f'backup_{timestamp}.json'
            self.backup_django_dumpdata(backup_dir / filename)
        else:
            ext = 'sql' if backup_format == 'sql' else 'dump'
            filename = f'backup_{timestamp}.{ext}'
            self.backup_pg_dump(database_url, backup_dir / filename, backup_format)

        self.stdout.write(self.style.SUCCESS(f'Backup created: {backup_dir / filename}'))

        # Clean up old backups
        if options['keep'] > 0:
            self.cleanup_old_backups(backup_dir, options['keep'], backup_format)

    def backup_pg_dump(self, database_url, output_path, format_type):
        """Backup using pg_dump."""
        # Check if pg_dump is available
        try:
            subprocess.run(['pg_dump', '--version'], capture_output=True, check=True)
        except FileNotFoundError:
            raise CommandError(
                'pg_dump not found. Install PostgreSQL client tools:\n'
                '  macOS: brew install postgresql\n'
                '  Ubuntu: sudo apt-get install postgresql-client'
            )

        # Build pg_dump command
        cmd = ['pg_dump', database_url]
        if format_type == 'custom':
            cmd.extend(['-Fc'])  # Custom format (compressed, supports pg_restore)

        cmd.extend(['-f', str(output_path)])

        self.stdout.write(f'Running pg_dump...')
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stderr:
                self.stdout.write(self.style.WARNING(result.stderr))
        except subprocess.CalledProcessError as e:
            raise CommandError(f'pg_dump failed: {e.stderr}')

    def backup_django_dumpdata(self, output_path):
        """Backup using Django's dumpdata."""
        from django.core.management import call_command
        from io import StringIO

        self.stdout.write('Running Django dumpdata...')
        output = StringIO()
        call_command(
            'dumpdata',
            exclude=['contenttypes', 'auth.permission'],
            indent=2,
            stdout=output
        )
        output_path.write_text(output.getvalue())

    def cleanup_old_backups(self, backup_dir, keep_count, format_type):
        """Remove old backups, keeping only the most recent ones."""
        if format_type == 'json':
            pattern = 'backup_*.json'
        elif format_type == 'sql':
            pattern = 'backup_*.sql'
        else:
            pattern = 'backup_*.dump'

        backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        if len(backups) > keep_count:
            for old_backup in backups[keep_count:]:
                old_backup.unlink()
                self.stdout.write(f'Removed old backup: {old_backup.name}')
