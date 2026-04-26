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
            default=1,
            help='Seconds between connection attempts (default: 1)'
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        interval = options['interval']

        self.stdout.write('Waiting for database...')

        start_time = time.time()
        db_conn = None

        while time.time() - start_time < timeout:
            try:
                db_conn = connections['default']
                db_conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS('Database available!'))
                return
            except OperationalError as e:
                elapsed = int(time.time() - start_time)
                self.stdout.write(f'Database unavailable ({elapsed}s): {e}')
                time.sleep(interval)

        self.stdout.write(self.style.ERROR(
            f'Database not available after {timeout} seconds'
        ))
        raise SystemExit(1)
