import logging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import (
    Dilemma, Participant, TIPIResponse, Rating, ChatTurn, EventLog,
    DebriefResponse, SystemPromptLog, StanceCombination
)
from .export import export_participants_json, export_participants_csv


# GDPR audit logger - logs to file, not EventLog (which gets deleted)
gdpr_logger = logging.getLogger('gdpr_audit')


class ReadOnlyAdminMixin:
    """Mixin to make admin read-only (no add/change, but allows delete for cascade)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion so participant cascade deletes work
        return True


@admin.register(Dilemma)
class DilemmaAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['code', 'author', 'category', 'dilemma_type', 'variation_type', 'researcher', 'low_rating_framework', 'text_preview']
    search_fields = ['code', 'text', 'subject', 'researcher', 'base_dilemma_code']
    list_filter = ['author', 'category', 'dilemma_type', 'variation_type', 'low_rating_framework', 'researcher']

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Text'


@admin.register(StanceCombination)
class StanceCombinationAdmin(admin.ModelAdmin):
    list_display = ['combination_index', 'short_desc', 'reinforces', 'challenges', 'usage_count']
    list_filter = ['combination_index']
    ordering = ['combination_index']
    readonly_fields = ['combination_index', 'usage_count', 'description', 'short_description']

    def short_desc(self, obj):
        return obj.short_description
    short_desc.short_description = 'Assignment Pattern'

    def reinforces(self, obj):
        info = obj.COMBINATION_DESCRIPTIONS.get(obj.combination_index, {})
        return ', '.join(info.get('same', []))
    reinforces.short_description = 'LLM Reinforces (same stance)'

    def challenges(self, obj):
        info = obj.COMBINATION_DESCRIPTIONS.get(obj.combination_index, {})
        return ', '.join(info.get('opposite', []))
    challenges.short_description = 'LLM Challenges (opposite stance)'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Inline admins for Participant detail view
class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    can_delete = False
    fields = ['dilemma', 'phase', 'rating', 'created_at']
    readonly_fields = ['dilemma', 'phase', 'rating', 'created_at']
    ordering = ['phase', 'created_at']

    def has_add_permission(self, request, obj=None):
        return False


class ChatTurnInline(admin.TabularInline):
    model = ChatTurn
    extra = 0
    can_delete = False
    fields = ['dilemma', 'sender', 'text_preview', 'timestamp']
    readonly_fields = ['dilemma', 'sender', 'text_preview', 'timestamp']
    ordering = ['dilemma', 'timestamp']

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Message'

    def has_add_permission(self, request, obj=None):
        return False


class SystemPromptLogInline(admin.TabularInline):
    model = SystemPromptLog
    extra = 0
    can_delete = False
    fields = ['dilemma', 'llm_framework', 'stance_mode', 'llm_position', 'created_at']
    readonly_fields = ['dilemma', 'llm_framework', 'stance_mode', 'llm_position', 'created_at']
    ordering = ['created_at']

    def has_add_permission(self, request, obj=None):
        return False


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
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'prolific_id', 'condition', 'llm_provider', 'status', 'stance_combination_used', 'koerner_chat_cost_category', 'attention_check_result', 'created_at', 'withdrawn']
    list_filter = ['condition', 'llm_provider', 'status', 'withdrawn', 'stance_combination_used', 'koerner_chat_cost_category', 'attention_check_phase', 'attention_check_passed']
    search_fields = ['prolific_id', 'session_key']
    date_hierarchy = 'created_at'
    actions = [delete_participant_data]
    change_list_template = 'admin/experiment/participant/change_list.html'
    inlines = [RatingInline, ChatTurnInline, SystemPromptLogInline]

    fieldsets = (
        ('Participant Info', {
            'fields': ('prolific_id', 'session_key', 'condition', 'llm_provider', 'status', 'withdrawn', 'created_at', 'completed_at')
        }),
        ('Dilemma Assignments', {
            'fields': ('rating_dilemmas_display', 'chat_dilemmas_display', 'stance_assignments_display'),
            'description': 'Shows which dilemmas were assigned and how'
        }),
        ('Stance Configuration', {
            'fields': ('stance_combination_used', 'stance_combination_description', 'koerner_chat_cost_category', 'nonmoral_dilemma_id')
        }),
        ('Attention Check', {
            'fields': ('attention_check_phase', 'attention_check_position', 'attention_check_passed', 'attention_check_response')
        }),
    )

    readonly_fields = [
        'prolific_id', 'session_key', 'condition', 'llm_provider', 'status', 'withdrawn',
        'created_at', 'completed_at', 'stance_combination_used', 'koerner_chat_cost_category',
        'nonmoral_dilemma_id', 'attention_check_phase', 'attention_check_position',
        'attention_check_passed', 'attention_check_response',
        'rating_dilemmas_display', 'chat_dilemmas_display', 'stance_assignments_display',
        'stance_combination_description'
    ]

    def attention_check_result(self, obj):
        if obj.attention_check_passed is None:
            return '-'
        elif obj.attention_check_passed:
            return f'✓ ({obj.attention_check_phase})'
        else:
            return f'✗ {obj.attention_check_response} ({obj.attention_check_phase})'
    attention_check_result.short_description = 'Attention Check'

    def rating_dilemmas_display(self, obj):
        """Show all dilemmas assigned for rating in order."""
        dilemma_ids = obj.all_dilemma_order
        if not dilemma_ids:
            return '-'
        dilemmas = Dilemma.objects.filter(id__in=dilemma_ids)
        dilemma_map = {d.id: d for d in dilemmas}
        lines = []
        for i, did in enumerate(dilemma_ids, 1):
            d = dilemma_map.get(did)
            if d:
                lines.append(f"{i}. {d.code} ({d.category})")
        return '\n'.join(lines) if lines else '-'
    rating_dilemmas_display.short_description = 'Rating Dilemmas (in order)'

    def chat_dilemmas_display(self, obj):
        """Show dilemmas assigned for chat discussion."""
        dilemma_ids = obj.chat_dilemma_ids
        if not dilemma_ids:
            return '-'
        dilemmas = Dilemma.objects.filter(id__in=dilemma_ids)
        dilemma_map = {d.id: d for d in dilemmas}
        stances = obj.stance_assignments
        lines = []
        for i, did in enumerate(dilemma_ids, 1):
            d = dilemma_map.get(did)
            stance = stances.get(str(did), 'unknown')
            if d:
                lines.append(f"{i}. {d.code} ({d.category}) - stance: {stance}")
        return '\n'.join(lines) if lines else '-'
    chat_dilemmas_display.short_description = 'Chat Dilemmas (with stance)'

    def stance_assignments_display(self, obj):
        """Show stance assignments in readable format."""
        stances = obj.stance_assignments
        if not stances:
            return '-'
        dilemma_ids = [int(k) for k in stances.keys()]
        dilemmas = Dilemma.objects.filter(id__in=dilemma_ids)
        dilemma_map = {d.id: d for d in dilemmas}

        same = []
        opposite = []
        for did_str, stance in stances.items():
            d = dilemma_map.get(int(did_str))
            if d:
                if stance == 'same':
                    same.append(d.code)
                elif stance == 'opposite':
                    opposite.append(d.code)

        result = []
        if same:
            result.append(f"LLM reinforces (same): {', '.join(same)}")
        if opposite:
            result.append(f"LLM challenges (opposite): {', '.join(opposite)}")
        return '\n'.join(result) if result else '-'
    stance_assignments_display.short_description = 'Stance Summary'

    def stance_combination_description(self, obj):
        """Show description of the stance combination used."""
        if obj.stance_combination_used is None:
            return '-'
        try:
            sc = StanceCombination.objects.get(combination_index=obj.stance_combination_used)
            return sc.description
        except StanceCombination.DoesNotExist:
            return f'Combination {obj.stance_combination_used} (not found)'
    stance_combination_description.short_description = 'Combination Description'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing but all fields are read-only
        return True

    def has_delete_permission(self, request, obj=None):
        # Allow deletion for GDPR compliance
        return True

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Hide save buttons since everything is read-only
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)


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
    list_display = ['participant', 'dilemma', 'sender', 'text_preview', 'timestamp_with_seconds']
    list_filter = ['sender', 'dilemma', 'timestamp']
    search_fields = ['participant__prolific_id', 'text']

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'

    def timestamp_with_seconds(self, obj):
        return obj.timestamp.strftime('%b %d, %Y, %H:%M:%S')
    timestamp_with_seconds.short_description = 'Timestamp'
    timestamp_with_seconds.admin_order_field = 'timestamp'


@admin.register(EventLog)
class EventLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'event_type', 'page', 'timestamp_with_seconds']
    list_filter = ['event_type', 'page', 'timestamp']
    search_fields = ['participant__prolific_id', 'event_type']
    date_hierarchy = 'timestamp'

    def timestamp_with_seconds(self, obj):
        return obj.timestamp.strftime('%b %d, %Y, %H:%M:%S')
    timestamp_with_seconds.short_description = 'Timestamp'
    timestamp_with_seconds.admin_order_field = 'timestamp'


@admin.register(DebriefResponse)
class DebriefResponseAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'age', 'gender', 'education', 'native_english', 'ai_trust', 'ai_usage_frequency', 'noticed_persuasion', 'changed_mind', 'has_email', 'created_at']
    list_filter = ['gender', 'education', 'native_english', 'ai_trust', 'ai_usage_frequency', 'noticed_persuasion', 'changed_mind', 'created_at']
    search_fields = ['participant__prolific_id', 'general_feedback', 'results_email']

    def has_email(self, obj):
        return bool(obj.results_email)
    has_email.boolean = True
    has_email.short_description = 'Email'


@admin.register(SystemPromptLog)
class SystemPromptLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'dilemma', 'condition', 'llm_framework', 'stance_mode', 'llm_position', 'created_at']
    list_filter = ['condition', 'llm_framework', 'stance_mode', 'llm_position', 'created_at']
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

    def delete_all_view(request):
        """Delete all participant data with confirmation."""
        if request.method == 'POST':
            if request.POST.get('confirm') == 'DELETE ALL':
                # Count before deletion
                participant_count = Participant.objects.count()

                # Log the bulk deletion
                gdpr_logger.info(
                    f"BULK DELETION: All {participant_count} participants deleted, "
                    f"Deleted by={request.user.username}, "
                    f"Timestamp={timezone.now().isoformat()}"
                )

                # Delete all participants (cascades to related data)
                Participant.objects.all().delete()

                # Reset stance combination counters
                StanceCombination.objects.all().update(usage_count=0)

                from django.contrib import messages
                messages.success(request, f"Successfully deleted {participant_count} participant(s) and all associated data. Stance combination counters have been reset.")

                from django.shortcuts import redirect
                return redirect('admin:experiment_participant_changelist')
            else:
                from django.contrib import messages
                messages.error(request, "Deletion cancelled. You must type 'DELETE ALL' to confirm.")

        # GET request - show confirmation form
        context = {
            'title': 'Delete All Participant Data',
            'participant_count': Participant.objects.count(),
            'rating_count': Rating.objects.count(),
            'chat_turn_count': ChatTurn.objects.count(),
            'event_log_count': EventLog.objects.count(),
            'debrief_count': DebriefResponse.objects.count(),
            'tipi_count': TIPIResponse.objects.count(),
            'system_prompt_count': SystemPromptLog.objects.count(),
        }
        return render(request, 'admin/experiment/delete_all.html', context)

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
        path('experiment/delete-all/', admin.site.admin_view(delete_all_view), name='experiment_delete_all'),
    ]
    return custom_urls + original_get_urls()


admin.site.get_urls = get_urls_with_export
