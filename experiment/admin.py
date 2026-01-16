from django.contrib import admin
from .models import (
    Dilemma, Participant, TIPIResponse, Rating, ChatTurn, EventLog, DebriefResponse
)


@admin.register(Dilemma)
class DilemmaAdmin(admin.ModelAdmin):
    list_display = ['code', 'text_preview']
    search_fields = ['code', 'text']

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text'


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'prolific_id', 'condition', 'llm_provider', 'status', 'created_at', 'withdrawn']
    list_filter = ['condition', 'llm_provider', 'status', 'withdrawn']
    search_fields = ['prolific_id', 'session_key']
    readonly_fields = ['session_key', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'


@admin.register(TIPIResponse)
class TIPIResponseAdmin(admin.ModelAdmin):
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
class RatingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'phase', 'rating', 'created_at']
    list_filter = ['phase', 'dilemma', 'created_at']
    search_fields = ['participant__prolific_id']


@admin.register(ChatTurn)
class ChatTurnAdmin(admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'sender', 'text_preview', 'timestamp']
    list_filter = ['sender', 'dilemma', 'timestamp']
    search_fields = ['participant__prolific_id', 'text']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ['participant', 'event_type', 'page', 'timestamp']
    list_filter = ['event_type', 'page', 'timestamp']
    search_fields = ['participant__prolific_id', 'event_type']
    date_hierarchy = 'timestamp'


@admin.register(DebriefResponse)
class DebriefResponseAdmin(admin.ModelAdmin):
    list_display = ['participant', 'noticed_persuasion', 'changed_mind', 'created_at']
    list_filter = ['noticed_persuasion', 'changed_mind', 'created_at']
    search_fields = ['participant__prolific_id', 'general_feedback']
