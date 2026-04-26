"""
Management command to wait for the database to be available.
Use this before running migrations in production to handle timing issues.
"""
import time
import socket
import os
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings


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

        # Debug: show database configuration
        db_settings = settings.DATABASES.get('default', {})
        host = db_settings.get('HOST', 'not set')
        port = db_settings.get('PORT', 'not set')
        engine = db_settings.get('ENGINE', 'not set')
        self.stdout.write(f'[DEBUG] DB Engine: {engine}')
        self.stdout.write(f'[DEBUG] DB Host: {host}')
        self.stdout.write(f'[DEBUG] DB Port: {port}')
        self.stdout.write(f'[DEBUG] DB Options: {db_settings.get("OPTIONS", {})}')

        # Test DNS resolution
        self.stdout.write(f'[DEBUG] Testing DNS resolution for {host}...')
        try:
            ip = socket.gethostbyname(host)
            self.stdout.write(f'[DEBUG] DNS resolved: {host} -> {ip}')
        except socket.gaierror as e:
            self.stdout.write(self.style.ERROR(f'[DEBUG] DNS failed: {e}'))

        # Test raw TCP connection
        self.stdout.write(f'[DEBUG] Testing TCP connection to {host}:{port}...')
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, int(port) if port else 5432))
            sock.close()
            if result == 0:
                self.stdout.write(self.style.SUCCESS(f'[DEBUG] TCP connection successful'))
            else:
                self.stdout.write(self.style.ERROR(f'[DEBUG] TCP connection failed: error code {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[DEBUG] TCP test error: {e}'))

        self.stdout.write('Waiting for database...')

        start_time = time.time()

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
            except Exception as e:
                elapsed = int(time.time() - start_time)
                self.stdout.write(f'Unexpected error ({elapsed}s): {type(e).__name__}: {e}')
                time.sleep(interval)

        self.stdout.write(self.style.ERROR(
            f'Database not available after {timeout} seconds'
        ))
        raise SystemExit(1)
