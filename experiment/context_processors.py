"""
Custom context processors for the experiment app.
"""
from django.conf import settings


def debug_context(request):
    """Add DEBUG setting to template context."""
    return {'debug': settings.DEBUG}
