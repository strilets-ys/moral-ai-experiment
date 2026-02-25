import logging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import (
    Dilemma, Participant, TIPIResponse, Rating, ChatTurn, EventLog,
    DebriefResponse, SystemPromptLog
)
from .export import export_participants_json, export_participants_csv


# GDPR audit logger - logs to file, not EventLog (which gets deleted)
gdpr_logger = logging.getLogger('gdpr_audit')


class ReadOnlyAdminMixin:
    """Mixin to make admin read-only (no add/change/delete)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Dilemma)
class DilemmaAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'researcher', 'dilemma_type', 'subject', 'low_rating_framework', 'text_preview']
    search_fields = ['code', 'text', 'subject', 'researcher']
    list_filter = ['dilemma_type', 'low_rating_framework', 'researcher']

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text'


@admin.action(description='Delete participant data (GDPR request)')
def delete_participant_data(modeladmin, request, queryset):
    """GDPR-compliant deletion with audit logging."""
    for p in queryset:
        gdpr_logger.info(
            f"GDPR deletion: Participant ID={p.id}, "
            f"Prolific={p.prolific_id}, "
            f"Condition={p.condition}, "
            f"Status={p.status}, "
            f"Deleted by={request.user.username}, "
            f"Timestamp={timezone.now().isoformat()}"
        )
    count = queryset.count()
    queryset.delete()
    modeladmin.message_user(request, f"Deleted {count} participant(s) and all associated data.")


@admin.register(Participant)
class ParticipantAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'prolific_id', 'condition', 'llm_provider', 'status', 'created_at', 'withdrawn']
    list_filter = ['condition', 'llm_provider', 'status', 'withdrawn']
    search_fields = ['prolific_id', 'session_key']
    readonly_fields = ['session_key', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'
    actions = [delete_participant_data]

    def has_delete_permission(self, request, obj=None):
        # Allow deletion for GDPR compliance
        return True


@admin.register(TIPIResponse)
class TIPIResponseAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'extraversion', 'agreeableness', 'conscientiousness',
                    'emotional_stability', 'openness', 'created_at']
    list_filter = ['created_at']
    search_fields = ['participant__prolific_id']

    def extraversion(self, obj):
        return f'{obj.extraversion:.1f}'

    def agreeableness(self, obj):
        return f'{obj.agreeableness:.1f}'

    def conscientiousness(self, obj):
        return f'{obj.conscientiousness:.1f}'

    def emotional_stability(self, obj):
        return f'{obj.emotional_stability:.1f}'

    def openness(self, obj):
        return f'{obj.openness:.1f}'


@admin.register(Rating)
class RatingAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'phase', 'rating', 'created_at']
    list_filter = ['phase', 'dilemma', 'created_at']
    search_fields = ['participant__prolific_id']


@admin.register(ChatTurn)
class ChatTurnAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'sender', 'text_preview', 'timestamp']
    list_filter = ['sender', 'dilemma', 'timestamp']
    search_fields = ['participant__prolific_id', 'text']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'


@admin.register(EventLog)
class EventLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'event_type', 'page', 'timestamp']
    list_filter = ['event_type', 'page', 'timestamp']
    search_fields = ['participant__prolific_id', 'event_type']
    date_hierarchy = 'timestamp'


@admin.register(DebriefResponse)
class DebriefResponseAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'noticed_persuasion', 'changed_mind', 'created_at']
    list_filter = ['noticed_persuasion', 'changed_mind', 'created_at']
    search_fields = ['participant__prolific_id', 'general_feedback']


@admin.register(SystemPromptLog)
class SystemPromptLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'condition', 'llm_framework', 'created_at']
    list_filter = ['condition', 'llm_framework', 'created_at']
    search_fields = ['participant__prolific_id', 'prompt_text']
    readonly_fields = ['prompt_text', 'personality_profile']


# Custom admin site to add export view
class ExperimentAdminSite(admin.AdminSite):
    """Custom admin site with export functionality."""

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('experiment/export/', self.admin_view(self.export_view), name='experiment_export'),
        ]
        return custom_urls + urls

    def export_view(self, request):
        """Export participant data as JSON or CSV."""
        if request.method == 'POST':
            # Get filter parameters
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')
            condition = request.POST.get('condition')
            status = request.POST.get('status')
            include_withdrawn = request.POST.get('include_withdrawn') == 'on'
            export_format = request.POST.get('format', 'json')

            # Build queryset
            queryset = Participant.objects.all()

            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            if condition:
                queryset = queryset.filter(condition=condition)
            if status:
                queryset = queryset.filter(status=status)
            if not include_withdrawn:
                queryset = queryset.filter(withdrawn=False)

            participant_ids = list(queryset.values_list('id', flat=True))

            if export_format == 'csv':
                content = export_participants_csv(participant_ids)
                response = HttpResponse(content, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="experiment_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            else:
                content = export_participants_json(participant_ids)
                response = HttpResponse(content, content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="experiment_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'

            return response

        # GET request - show the export form
        context = {
            'title': 'Export Experiment Data',
            'conditions': Participant.CONDITION_CHOICES,
            'statuses': Participant.STATUS_CHOICES,
            'participant_count': Participant.objects.count(),
            'non_withdrawn_count': Participant.objects.filter(withdrawn=False).count(),
        }
        return render(request, 'admin/experiment/export.html', context)


# Add export URL to the default admin site
original_get_urls = admin.site.get_urls


def get_urls_with_export():
    from django.urls import path

    def export_view(request):
        """Export participant data as JSON or CSV."""
        if request.method == 'POST':
            # Get filter parameters
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')
            condition = request.POST.get('condition')
            status = request.POST.get('status')
            include_withdrawn = request.POST.get('include_withdrawn') == 'on'
            export_format = request.POST.get('format', 'json')

            # Build queryset
            queryset = Participant.objects.all()

            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            if condition:
                queryset = queryset.filter(condition=condition)
            if status:
                queryset = queryset.filter(status=status)
            if not include_withdrawn:
                queryset = queryset.filter(withdrawn=False)

            participant_ids = list(queryset.values_list('id', flat=True))

            if export_format == 'csv':
                content = export_participants_csv(participant_ids)
                response = HttpResponse(content, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="experiment_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            else:
                content = export_participants_json(participant_ids)
                response = HttpResponse(content, content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="experiment_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'

            return response

        # GET request - show the export form
        context = {
            'title': 'Export Experiment Data',
            'conditions': Participant.CONDITION_CHOICES,
            'statuses': Participant.STATUS_CHOICES,
            'participant_count': Participant.objects.count(),
            'non_withdrawn_count': Participant.objects.filter(withdrawn=False).count(),
        }
        return render(request, 'admin/experiment/export.html', context)

    custom_urls = [
        path('experiment/export/', admin.site.admin_view(export_view), name='experiment_export'),
    ]
    return custom_urls + original_get_urls()


admin.site.get_urls = get_urls_with_export
