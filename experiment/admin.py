import logging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.html import format_html, escape

from .models import (
    Dilemma, Participant, TIPIResponse, Rating, ChatTurn, EventLog,
    DebriefResponse, SystemPromptLog, StanceCombination, DemographicsResponse,
    CompletionCell
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


@admin.register(CompletionCell)
class CompletionCellAdmin(admin.ModelAdmin):
    list_display = ['cell_display', 'condition', 'llm_provider', 'completion_count', 'target_count', 'progress_bar', 'is_complete']
    list_filter = ['condition', 'llm_provider']
    ordering = ['condition', 'llm_provider']
    readonly_fields = ['condition', 'llm_provider', 'completion_count', 'target_count']
    change_list_template = 'admin/experiment/completioncell/change_list.html'

    def cell_display(self, obj):
        return f"{obj.condition} + {obj.llm_provider}"
    cell_display.short_description = 'Cell'

    def progress_bar(self, obj):
        percentage = min(100, (obj.completion_count / obj.target_count * 100)) if obj.target_count > 0 else 0
        color = '#4caf50' if percentage >= 100 else '#2196f3'
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; height: 20px; text-align: center; color: white; font-size: 11px; line-height: 20px;">'
            '{}/{}</div></div>',
            percentage, color, obj.completion_count, obj.target_count
        )
    progress_bar.short_description = 'Progress'

    def is_complete(self, obj):
        return obj.completion_count >= obj.target_count
    is_complete.boolean = True
    is_complete.short_description = 'Full'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Add summary statistics
        extra_context = extra_context or {}
        cells = CompletionCell.objects.all()
        total_completions = sum(c.completion_count for c in cells)
        total_target = sum(c.target_count for c in cells)
        extra_context['total_completions'] = total_completions
        extra_context['total_target'] = total_target
        extra_context['total_percentage'] = (total_completions / total_target * 100) if total_target > 0 else 0

        # Summary by condition
        condition_summary = {}
        for cell in cells:
            if cell.condition not in condition_summary:
                condition_summary[cell.condition] = {'completions': 0, 'target': 0}
            condition_summary[cell.condition]['completions'] += cell.completion_count
            condition_summary[cell.condition]['target'] += cell.target_count
        extra_context['condition_summary'] = condition_summary

        # Summary by LLM
        llm_summary = {}
        for cell in cells:
            if cell.llm_provider not in llm_summary:
                llm_summary[cell.llm_provider] = {'completions': 0, 'target': 0}
            llm_summary[cell.llm_provider]['completions'] += cell.completion_count
            llm_summary[cell.llm_provider]['target'] += cell.target_count
        extra_context['llm_summary'] = llm_summary

        return super().changelist_view(request, extra_context)


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


class SystemPromptLogInline(admin.StackedInline):
    model = SystemPromptLog
    extra = 0
    can_delete = False
    fields = ['dilemma', 'llm_framework', 'stance_mode', 'llm_position', 'prompt_text_display', 'personality_profile_display', 'created_at']
    readonly_fields = ['dilemma', 'llm_framework', 'stance_mode', 'llm_position', 'prompt_text_display', 'personality_profile_display', 'created_at']
    ordering = ['created_at']

    def prompt_text_display(self, obj):
        """Display full prompt text in a readable format."""
        if not obj.prompt_text:
            return '-'
        # Format the prompt text with proper styling
        html = f'<pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px; max-height: 400px; overflow-y: auto; font-family: monospace;">{escape(obj.prompt_text)}</pre>'
        return format_html(html)
    prompt_text_display.short_description = 'Full System Prompt'

    def personality_profile_display(self, obj):
        """Display personality profile if present."""
        if not obj.personality_profile:
            return '-'
        # Format the personality profile nicely
        html = f'<pre style="white-space: pre-wrap; word-wrap: break-word; background: #e8f5e9; padding: 12px; border-radius: 4px; font-size: 12px; font-family: monospace;">{escape(obj.personality_profile)}</pre>'
        return format_html(html)
    personality_profile_display.short_description = 'Personality Profile'

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description='Delete participant data (GDPR request)')
def delete_participant_data(modeladmin, request, queryset):
    """GDPR-compliant deletion with audit logging and explicit cascade."""
    count = queryset.count()
    participant_ids = list(queryset.values_list('id', flat=True))

    # Count related data for logging
    related_counts = {
        'ratings': Rating.objects.filter(participant_id__in=participant_ids).count(),
        'chat_turns': ChatTurn.objects.filter(participant_id__in=participant_ids).count(),
        'events': EventLog.objects.filter(participant_id__in=participant_ids).count(),
        'system_prompts': SystemPromptLog.objects.filter(participant_id__in=participant_ids).count(),
        'tipi': TIPIResponse.objects.filter(participant_id__in=participant_ids).count(),
        'demographics': DemographicsResponse.objects.filter(participant_id__in=participant_ids).count(),
        'debrief': DebriefResponse.objects.filter(participant_id__in=participant_ids).count(),
    }

    # Decrement CompletionCell counters for completed participants
    completed_cells_decremented = 0
    for p in queryset:
        gdpr_logger.info(
            f"GDPR deletion: Participant ID={p.id}, "
            f"Prolific={p.prolific_id}, "
            f"Condition={p.condition}, "
            f"Status={p.status}, "
            f"Deleted by={request.user.username}, "
            f"Timestamp={timezone.now().isoformat()}"
        )
        # Decrement completion cell if participant was completed
        if p.status == 'complete':
            try:
                cell = CompletionCell.objects.get(condition=p.condition, llm_provider=p.llm_provider)
                if cell.completion_count > 0:
                    cell.completion_count -= 1
                    cell.save()
                    completed_cells_decremented += 1
            except CompletionCell.DoesNotExist:
                pass

    # Explicit cascade delete to ensure all related data is removed
    Rating.objects.filter(participant_id__in=participant_ids).delete()
    ChatTurn.objects.filter(participant_id__in=participant_ids).delete()
    EventLog.objects.filter(participant_id__in=participant_ids).delete()
    SystemPromptLog.objects.filter(participant_id__in=participant_ids).delete()
    TIPIResponse.objects.filter(participant_id__in=participant_ids).delete()
    DemographicsResponse.objects.filter(participant_id__in=participant_ids).delete()
    DebriefResponse.objects.filter(participant_id__in=participant_ids).delete()

    # Now delete participants
    queryset.delete()

    total_related = sum(related_counts.values())
    completion_msg = f" Decremented {completed_cells_decremented} completion cell(s)." if completed_cells_decremented > 0 else ""
    modeladmin.message_user(
        request,
        f"Deleted {count} participant(s) and {total_related} related records: "
        f"{related_counts['ratings']} ratings, {related_counts['chat_turns']} chat turns, "
        f"{related_counts['events']} events, {related_counts['system_prompts']} prompts, "
        f"{related_counts['tipi']} TIPI, {related_counts['demographics']} demographics, "
        f"{related_counts['debrief']} debrief responses.{completion_msg}"
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'prolific_id', 'condition', 'llm_provider', 'status', 'completion_code', 'stance_combination_used', 'koerner_chat_cost_category', 'attention_check_result', 'created_at', 'withdrawn']
    list_filter = ['condition', 'llm_provider', 'status', 'withdrawn', 'stance_combination_used', 'koerner_chat_cost_category', 'attention_check_phase', 'attention_check_passed']
    search_fields = ['prolific_id', 'session_key']
    date_hierarchy = 'created_at'
    actions = [delete_participant_data]
    change_list_template = 'admin/experiment/participant/change_list.html'
    inlines = [SystemPromptLogInline]  # Rating and Chat now shown in custom displays above

    fieldsets = (
        ('Participant Info', {
            'fields': ('prolific_id', 'session_key', 'condition', 'llm_provider', 'status', 'completion_code', 'withdrawn', 'created_at', 'completed_at')
        }),
        ('Rating Comparison', {
            'fields': ('rating_comparison_display',),
            'description': 'Pre and post ratings for each dilemma with change indicators'
        }),
        ('Chat Transcripts', {
            'fields': ('chat_transcripts_display',),
            'description': 'Full chat conversations grouped by dilemma'
        }),
        ('Dilemma Assignments', {
            'fields': ('rating_dilemmas_display', 'chat_dilemmas_display', 'stance_assignments_display'),
            'description': 'Shows which dilemmas were assigned and how',
            'classes': ('collapse',)
        }),
        ('Stance Configuration', {
            'fields': ('stance_combination_used', 'stance_combination_description', 'koerner_chat_cost_category'),
            'classes': ('collapse',)
        }),
        ('Attention Check', {
            'fields': ('attention_check_phase', 'attention_check_position', 'attention_check_passed', 'attention_check_response'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = [
        'prolific_id', 'session_key', 'condition', 'llm_provider', 'status', 'completion_code', 'withdrawn',
        'created_at', 'completed_at', 'stance_combination_used', 'koerner_chat_cost_category',
        'attention_check_phase', 'attention_check_position',
        'attention_check_passed', 'attention_check_response',
        'rating_dilemmas_display', 'chat_dilemmas_display', 'stance_assignments_display',
        'stance_combination_description', 'rating_comparison_display', 'chat_transcripts_display'
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

    def rating_comparison_display(self, obj):
        """Show pre and post ratings side by side for each dilemma."""
        ratings = Rating.objects.filter(participant=obj).select_related('dilemma')

        # Build dict of ratings by dilemma
        pre_ratings = {}
        post_ratings = {}
        for r in ratings:
            if r.phase == 'pre':
                pre_ratings[r.dilemma_id] = r.rating
            else:
                post_ratings[r.dilemma_id] = r.rating

        # Get all dilemmas for this participant
        all_dilemma_ids = obj.all_dilemma_order or []
        if not all_dilemma_ids:
            return '-'

        dilemmas = Dilemma.objects.filter(id__in=all_dilemma_ids)
        dilemma_map = {d.id: d for d in dilemmas}
        chat_dilemma_ids = set(obj.chat_dilemma_ids or [])
        stances = obj.stance_assignments or {}

        html = ['<table style="border-collapse: collapse; width: 100%;">']
        html.append('<thead><tr style="background: #f0f0f0;">')
        html.append('<th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Dilemma</th>')
        html.append('<th style="padding: 8px; border: 1px solid #ddd; text-align: center; width: 80px;">Pre</th>')
        html.append('<th style="padding: 8px; border: 1px solid #ddd; text-align: center; width: 80px;">Post</th>')
        html.append('<th style="padding: 8px; border: 1px solid #ddd; text-align: center; width: 80px;">Change</th>')
        html.append('<th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Chat Info</th>')
        html.append('</tr></thead><tbody>')

        for did in all_dilemma_ids:
            d = dilemma_map.get(did)
            if not d:
                continue

            pre = pre_ratings.get(did)
            post = post_ratings.get(did)
            is_chat = did in chat_dilemma_ids
            stance = stances.get(str(did), '')

            # Calculate change
            if pre is not None and post is not None:
                change = post - pre
                if change > 0:
                    change_str = f'<span style="color: green;">+{change}</span>'
                elif change < 0:
                    change_str = f'<span style="color: red;">{change}</span>'
                else:
                    change_str = '<span style="color: gray;">0</span>'
            else:
                change_str = '-'

            # Chat info
            if is_chat:
                stance_label = 'reinforce' if stance == 'same' else 'challenge'
                chat_info = f'<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">Chat ({stance_label})</span>'
            else:
                chat_info = '<span style="color: #999;">No chat</span>'

            html.append(f'<tr>')
            html.append(f'<td style="padding: 8px; border: 1px solid #ddd;"><strong>{escape(d.code)}</strong> <span style="color: #666;">({d.category})</span></td>')
            html.append(f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{pre if pre is not None else "-"}</td>')
            html.append(f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{post if post is not None else "-"}</td>')
            html.append(f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{change_str}</td>')
            html.append(f'<td style="padding: 8px; border: 1px solid #ddd;">{chat_info}</td>')
            html.append('</tr>')

        html.append('</tbody></table>')
        return format_html(''.join(html))
    rating_comparison_display.short_description = 'Rating Comparison (Pre vs Post)'

    def chat_transcripts_display(self, obj):
        """Show full chat transcripts grouped by dilemma."""
        chat_turns = ChatTurn.objects.filter(participant=obj).select_related('dilemma').order_by('dilemma_id', 'timestamp')

        if not chat_turns.exists():
            return '-'

        # Group by dilemma
        turns_by_dilemma = {}
        for turn in chat_turns:
            if turn.dilemma_id not in turns_by_dilemma:
                turns_by_dilemma[turn.dilemma_id] = []
            turns_by_dilemma[turn.dilemma_id].append(turn)

        # Get dilemma info
        dilemma_ids = list(turns_by_dilemma.keys())
        dilemmas = Dilemma.objects.filter(id__in=dilemma_ids)
        dilemma_map = {d.id: d for d in dilemmas}

        # Get stance info and ratings
        stances = obj.stance_assignments or {}
        pre_ratings = {r.dilemma_id: r.rating for r in Rating.objects.filter(participant=obj, phase='pre')}
        post_ratings = {r.dilemma_id: r.rating for r in Rating.objects.filter(participant=obj, phase='post')}

        # Get system prompts
        prompts = SystemPromptLog.objects.filter(participant=obj)
        prompt_map = {p.dilemma_id: p for p in prompts}

        html = []

        for did in obj.chat_dilemma_ids or []:
            if did not in turns_by_dilemma:
                continue

            d = dilemma_map.get(did)
            turns = turns_by_dilemma[did]
            stance = stances.get(str(did), 'unknown')
            prompt_log = prompt_map.get(did)

            pre = pre_ratings.get(did, '-')
            post = post_ratings.get(did, '-')
            if pre != '-' and post != '-':
                change = post - pre
                change_str = f'+{change}' if change > 0 else str(change)
            else:
                change_str = '-'

            # Dilemma header
            html.append(f'<div style="margin-bottom: 24px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">')
            html.append(f'<div style="background: #f5f5f5; padding: 12px; border-bottom: 1px solid #ddd;">')
            html.append(f'<h3 style="margin: 0 0 8px 0; color: #333;">{escape(d.code if d else "Unknown")} <span style="font-weight: normal; color: #666;">({d.category if d else "-"})</span></h3>')

            # Stance and rating info
            stance_color = '#4caf50' if stance == 'same' else '#f44336'
            stance_label = 'Reinforce' if stance == 'same' else 'Challenge'
            html.append(f'<div style="display: flex; gap: 16px; font-size: 13px;">')
            html.append(f'<span><strong>Stance:</strong> <span style="color: {stance_color};">{stance_label}</span></span>')
            html.append(f'<span><strong>Pre:</strong> {pre}</span>')
            html.append(f'<span><strong>Post:</strong> {post}</span>')
            html.append(f'<span><strong>Change:</strong> {change_str}</span>')
            if prompt_log:
                html.append(f'<span><strong>Framework:</strong> {prompt_log.llm_framework}</span>')
                html.append(f'<span><strong>Position:</strong> {prompt_log.llm_position}</span>')
            html.append('</div>')
            html.append('</div>')

            # Chat messages
            html.append('<div style="padding: 12px;">')
            for turn in turns:
                if turn.sender == 'user':
                    bg_color = '#e3f2fd'
                    align = 'flex-end'
                    label = 'User'
                else:
                    bg_color = '#f5f5f5'
                    align = 'flex-start'
                    label = 'AI'

                timestamp = turn.timestamp.strftime('%H:%M:%S') if turn.timestamp else ''
                html.append(f'<div style="display: flex; justify-content: {align}; margin-bottom: 8px;">')
                html.append(f'<div style="max-width: 80%; background: {bg_color}; padding: 10px 14px; border-radius: 12px;">')
                html.append(f'<div style="font-size: 11px; color: #666; margin-bottom: 4px;"><strong>{label}</strong> &middot; {timestamp}</div>')
                html.append(f'<div style="white-space: pre-wrap; word-break: break-word;">{escape(turn.text)}</div>')
                html.append('</div></div>')

            html.append('</div></div>')

        return format_html(''.join(html)) if html else '-'
    chat_transcripts_display.short_description = 'Chat Transcripts'

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


@admin.register(DemographicsResponse)
class DemographicsResponseAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ['participant', 'age', 'gender', 'education', 'native_english', 'created_at']
    list_filter = ['gender', 'education', 'native_english', 'created_at']
    search_fields = ['participant__prolific_id']


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
    list_display = ['participant', 'stias_confident', 'stias_reliable', 'stias_trust', 'stias_avg', 'ai_usage_frequency', 'noticed_persuasion', 'changed_mind', 'has_email', 'created_at']
    list_filter = ['ai_usage_frequency', 'noticed_persuasion', 'changed_mind', 'created_at']
    search_fields = ['participant__prolific_id', 'general_feedback', 'results_email']

    def stias_avg(self, obj):
        avg = obj.stias_average
        return f'{avg:.2f}' if avg else '-'
    stias_avg.short_description = 'S-TIAS Avg'

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

                # Reset completion cell counters
                CompletionCell.objects.all().update(completion_count=0)

                from django.contrib import messages
                messages.success(request, f"Successfully deleted {participant_count} participant(s) and all associated data. Stance combination and completion cell counters have been reset.")

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
            'demographics_count': DemographicsResponse.objects.count(),
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
