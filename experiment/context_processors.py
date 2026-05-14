"""
Custom context processors for the experiment app.
"""
import os
from django.conf import settings


def debug_context(request):
    """Add DEBUG setting and timer enforcement flag to template context."""
    # Always enforce timer (duration is shortened in DEBUG mode via get_timer_seconds)
    return {
        'debug': settings.DEBUG,
        'is_production': True,  # Always enforce timer on button
    }
