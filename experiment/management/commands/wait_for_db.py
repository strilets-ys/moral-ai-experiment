"""
Management command to wait for the database to be available.
Use this before running migrations in production to handle timing issues.
"""
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Wait for database to be available'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Maximum seconds to wait for database (default: 30)'
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=2,
            help='Seconds between connection attempts (default: 2)'
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        interval = options['interval']

        self.stdout.write('Waiting for database...')
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                connections['default'].ensure_connection()
                self.stdout.write(self.style.SUCCESS('Database available!'))
                return
            except OperationalError:
                elapsed = int(time.time() - start_time)
                self.stdout.write(f'  Retrying... ({elapsed}s)')
                time.sleep(interval)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Unexpected error: {e}'))
                time.sleep(interval)

        self.stdout.write(self.style.ERROR(
            f'Database not available after {timeout} seconds'
        ))
        raise SystemExit(1)
