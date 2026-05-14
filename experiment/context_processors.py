"""
Custom context processors for the experiment app.
"""
import os
from django.conf import settings


def debug_context(request):
    """Add DEBUG setting and timer enforcement flag to template context."""
    # Enforce timer wait in production OR when explicitly enabled for testing
    # Check multiple indicators of production environment
    is_production_env = (
        not settings.DEBUG or
        os.environ.get('RAILWAY_ENVIRONMENT') is not None or
        os.environ.get('PRODUCTION', '').lower() == 'true' or
        os.environ.get('ENFORCE_TIMER_WAIT', '').lower() == 'true'
    )
    return {
        'debug': settings.DEBUG,
        'is_production': is_production_env,
    }
