"""
Custom context processors for the experiment app.
"""
import os
from django.conf import settings


def debug_context(request):
    """Add DEBUG setting and timer enforcement flag to template context."""
    # Enforce timer wait in production OR when explicitly enabled for testing
    enforce_timer = (
        not settings.DEBUG or
        os.environ.get('ENFORCE_TIMER_WAIT', '').lower() == 'true'
    )
    return {
        'debug': settings.DEBUG,
        'is_production': enforce_timer,
    }
