import json
import random
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.conf import settings

import logging

from .models import (
    Participant, Dilemma, TIPIResponse, Rating, ChatTurn, EventLog, DebriefResponse,
    SystemPromptLog, StanceCombination, DemographicsResponse, ATTENTION_CHECK_TEXT,
    CompletionCell
)
from .utils import generate_completion_code

logger = logging.getLogger(__name__)
from .llm import get_llm_client, build_system_prompt, test_llm_connection, get_llm_framework, get_llm_position


def get_timer_seconds(production_seconds: int) -> int:
    """Return short timer (5s) in DEBUG mode, full timer in production."""
    if settings.DEBUG:
        return 5
    return production_seconds


def get_or_create_participant(request):
    """Get participant from session or return None if not found."""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    try:
        return Participant.objects.get(session_key=session_key)
    except Participant.DoesNotExist:
        return None


def landing(request):
    """Landing page - capture Prolific ID and create participant."""
    # Check for existing participant
    participant = get_or_create_participant(request)

    if participant and not participant.withdrawn:
        # Resume from where they left off
        return redirect_to_current_stage(participant)

    # Get Prolific ID from URL params
    prolific_id = request.GET.get('PROLIFIC_PID', '')

    if request.method == 'POST':
        prolific_id = request.POST.get('prolific_id', prolific_id)

        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        # Weighted assignment for pilot study (inverse weights based on completion counts)
        condition, llm_provider = CompletionCell.get_weighted_assignment()

        # Create participant
        participant = Participant.objects.create(
            prolific_id=prolific_id if prolific_id else None,
            session_key=request.session.session_key,
            condition=condition,
            llm_provider=llm_provider,
            status='started',
        )

        # Assign dilemmas
        participant.assign_dilemmas()

        # Log event
        EventLog.objects.create(
            participant=participant,
            event_type='experiment_started',
            page='landing',
            data={'prolific_id': prolific_id, 'condition': condition, 'llm_provider': llm_provider}
        )

        return redirect('experiment:consent')

    return render(request, 'experiment/landing.html', {
        'prolific_id': prolific_id,
    })


def redirect_to_current_stage(participant):
    """Redirect participant to their current stage in the experiment."""
    status = participant.status

    if status == 'started':
        return redirect('experiment:consent')
    elif status == 'consent':
        return redirect('experiment:demographics')
    elif status == 'demographics':
        return redirect('experiment:tipi')
    elif status == 'tipi':
        return redirect('experiment:pre_rating', index=0)
    elif status == 'pre_rating':
        return redirect('experiment:chat', index=0)
    elif status == 'chat':
        return redirect('experiment:chat', index=participant.current_chat_index)
    elif status == 'post_rating':
        return redirect('experiment:debrief')
    elif status == 'debrief':
        return redirect('experiment:complete')
    elif status == 'complete':
        return redirect('experiment:complete')
    elif status == 'withdrawn':
        return redirect('experiment:withdrawn')
    elif status == 'attention_failed':
        return redirect('experiment:attention_failed')
    else:
        return redirect('experiment:landing')


def consent(request):
    """Display consent form and update status on agreement."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        if request.POST.get('consent') == 'agree':
            # Test LLM connection before proceeding
            success, error_message = test_llm_connection(participant.llm_provider)

            if not success:
                EventLog.objects.create(
                    participant=participant,
                    event_type='llm_connection_failed',
                    page='consent',
                    data={'provider': participant.llm_provider, 'error': error_message}
                )
                return redirect('experiment:connection_error')

            participant.status = 'consent'
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='consent_given',
                page='consent'
            )

            return redirect('experiment:demographics')
        else:
            # Did not consent - withdraw
            participant.status = 'withdrawn'
            participant.withdrawn = True
            participant.save()
            return redirect('experiment:withdrawn')

    return render(request, 'experiment/consent.html', {
        'participant': participant,
    })


def demographics(request):
    """Demographics form (collected before TIPI)."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        # Handle age
        age_str = request.POST.get('age', '')
        age = int(age_str) if age_str.isdigit() else None

        # Handle gender with "other" option
        gender = request.POST.get('gender', '')
        gender_other = request.POST.get('gender_other', '') if gender == 'other' else ''

        # Create DemographicsResponse
        DemographicsResponse.objects.update_or_create(
            participant=participant,
            defaults={
                'age': age,
                'gender': gender,
                'gender_other': gender_other,
                'education': request.POST.get('education', ''),
                'native_english': request.POST.get('native_english') == 'yes',
            }
        )

        participant.status = 'demographics'
        participant.save()

        EventLog.objects.create(
            participant=participant,
            event_type='demographics_completed',
            page='demographics',
            data={'age': age, 'gender': gender, 'education': request.POST.get('education', '')}
        )

        return redirect('experiment:tipi')

    return render(request, 'experiment/demographics.html', {
        'participant': participant,
    })


def tipi(request):
    """TIPI (Ten-Item Personality Inventory) form."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # TIPI items with labels
    tipi_items = [
        {'num': 1, 'label': 'Extraverted, enthusiastic'},
        {'num': 2, 'label': 'Critical, quarrelsome'},
        {'num': 3, 'label': 'Dependable, self-disciplined'},
        {'num': 4, 'label': 'Anxious, easily upset'},
        {'num': 5, 'label': 'Open to new experiences, complex'},
        {'num': 6, 'label': 'Reserved, quiet'},
        {'num': 7, 'label': 'Sympathetic, warm'},
        {'num': 8, 'label': 'Disorganized, careless'},
        {'num': 9, 'label': 'Calm, emotionally stable'},
        {'num': 10, 'label': 'Conventional, uncreative'},
    ]

    if request.method == 'POST':
        # Collect all 10 responses
        responses = {}
        for i in range(1, 11):
            value = request.POST.get(f'item_{i}')
            if value:
                responses[f'item_{i}'] = int(value)

        if len(responses) == 10:
            TIPIResponse.objects.create(
                participant=participant,
                **responses
            )

            participant.status = 'tipi'
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='tipi_completed',
                page='tipi',
                data=responses
            )

            return redirect('experiment:phase1_instructions')

    return render(request, 'experiment/tipi.html', {
        'participant': participant,
        'tipi_items': tipi_items,
        'timer_seconds': get_timer_seconds(120),  # 2 minutes
        'timer_enforce_wait': False,  # Timer is informational only
        'page_name': 'tipi',
    })


def phase1_instructions(request):
    """Phase 1 instruction page before initial dilemma ratings."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        EventLog.objects.create(
            participant=participant,
            event_type='phase1_instructions_acknowledged',
            page='phase1_instructions'
        )
        return redirect('experiment:pre_rating', index=0)

    return render(request, 'experiment/phase1_instructions.html', {
        'participant': participant,
        'page_name': 'phase1_instructions',
    })


def phase2_instructions(request):
    """Phase 2 instruction page before AI discussions."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        EventLog.objects.create(
            participant=participant,
            event_type='phase2_instructions_acknowledged',
            page='phase2_instructions'
        )
        return redirect('experiment:chat', index=0)

    return render(request, 'experiment/phase2_instructions.html', {
        'participant': participant,
        'page_name': 'phase2_instructions',
    })


def phase3_instructions(request):
    """Phase 3 instruction page before final dilemma ratings."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        EventLog.objects.create(
            participant=participant,
            event_type='phase3_instructions_acknowledged',
            page='phase3_instructions'
        )
        return redirect('experiment:post_rating', index=0)

    return render(request, 'experiment/phase3_instructions.html', {
        'participant': participant,
        'page_name': 'phase3_instructions',
    })


@never_cache
def pre_rating(request, index):
    """Rate one dilemma at a time before chat debates."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Get dilemmas in assigned order for pre-rating
    dilemma_ids = participant.pre_dilemma_order
    num_dilemmas = len(dilemma_ids)

    # Check if attention check is in this phase
    has_attention_check = participant.attention_check_phase == 'pre'
    attention_check_pos = participant.attention_check_position if has_attention_check else None

    # Total items: 9 dilemmas + 1 attention check if in this phase
    total_items = num_dilemmas + 1 if has_attention_check else num_dilemmas

    # Validate index
    if index < 0 or index >= total_items:
        return redirect('experiment:chat', index=0)

    # Determine if this index is the attention check
    is_attention_check = has_attention_check and index == attention_check_pos

    # Calculate dilemma index (adjusted for attention check position)
    if is_attention_check:
        dilemma = None
        dilemma_index = None
    elif has_attention_check and index > attention_check_pos:
        dilemma_index = index - 1
        try:
            dilemma = Dilemma.objects.get(id=dilemma_ids[dilemma_index])
        except Dilemma.DoesNotExist:
            return redirect('experiment:chat', index=0)
    else:
        dilemma_index = index
        try:
            dilemma = Dilemma.objects.get(id=dilemma_ids[dilemma_index])
        except Dilemma.DoesNotExist:
            return redirect('experiment:chat', index=0)

    # Server-side protection: check if already answered (prevent back-button modification)
    if is_attention_check:
        # Check if attention check was already answered
        if participant.attention_check_response is not None:
            EventLog.objects.create(
                participant=participant,
                event_type='attempted_attention_check_modification',
                page='pre_rating',
                data={'index': index, 'existing_response': participant.attention_check_response}
            )
            # If they failed, send them back to failed page
            if participant.status == 'attention_failed':
                return redirect('experiment:attention_failed')
            # Otherwise skip to next item
            if index + 1 < total_items:
                return redirect('experiment:pre_rating', index=index + 1)
            else:
                return redirect('experiment:phase2_instructions')
    elif dilemma:
        existing_rating = Rating.objects.filter(
            participant=participant,
            dilemma=dilemma,
            phase='pre'
        ).exists()
        if existing_rating:
            # Log the attempt and skip to next item
            EventLog.objects.create(
                participant=participant,
                event_type='attempted_rating_modification',
                page='pre_rating',
                data={'dilemma_id': dilemma.id, 'index': index}
            )
            # Move to next item or phase
            if index + 1 < total_items:
                return redirect('experiment:pre_rating', index=index + 1)
            else:
                return redirect('experiment:phase2_instructions')

    if request.method == 'POST':
        if is_attention_check:
            # Handle attention check response (only if not already answered)
            if participant.attention_check_response is None:
                rating_value = request.POST.get('rating_attention_check')
                if rating_value:
                    rating_int = int(rating_value)
                    participant.attention_check_response = rating_int
                    participant.attention_check_passed = (rating_int == 3)

                    EventLog.objects.create(
                        participant=participant,
                        event_type='attention_check_completed',
                        page='pre_rating',
                        data={
                            'response': rating_int,
                            'passed': rating_int == 3,
                            'position': index
                        }
                    )

                    # If attention check failed, end the survey immediately
                    if rating_int != 3:
                        participant.status = 'attention_failed'
                        participant.save()
                        return redirect('experiment:attention_failed')

                    participant.save()
        else:
            # Save rating for this dilemma
            rating_value = request.POST.get(f'rating_{dilemma.id}')
            if rating_value:
                # Use get_or_create to prevent rating modification
                Rating.objects.get_or_create(
                    participant=participant,
                    dilemma=dilemma,
                    phase='pre',
                    defaults={'rating': int(rating_value)}
                )

        # Move to next item or to chat
        if index + 1 < total_items:
            return redirect('experiment:pre_rating', index=index + 1)
        else:
            participant.status = 'pre_rating'
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='pre_rating_completed',
                page='pre_rating'
            )

            return redirect('experiment:phase2_instructions')

    return render(request, 'experiment/pre_rating.html', {
        'participant': participant,
        'dilemma': dilemma,
        'dilemma_index': index,
        'total_dilemmas': total_items,
        'is_attention_check': is_attention_check,
        'attention_check_text': ATTENTION_CHECK_TEXT if is_attention_check else None,
        'timer_seconds': get_timer_seconds(75),
        'page_name': f'pre_rating_{index}',
    })


def chat(request, index):
    """Chat interface for a specific dilemma."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Validate index
    chat_dilemma_ids = participant.chat_dilemma_ids
    if index < 0 or index >= len(chat_dilemma_ids):
        return redirect('experiment:phase3_instructions')

    # Get current dilemma
    try:
        dilemma = Dilemma.objects.get(id=chat_dilemma_ids[index])
    except Dilemma.DoesNotExist:
        return redirect('experiment:phase3_instructions')

    # Update current chat index
    participant.current_chat_index = index
    participant.status = 'chat'
    participant.save()

    # Get participant's pre-rating for this dilemma
    try:
        pre_rating = Rating.objects.get(
            participant=participant,
            dilemma=dilemma,
            phase='pre'
        )
        # Consistent with get_llm_framework(): 4 is neutral, not pro
        if pre_rating.rating > 4:
            participant_stance = 'pro'
        elif pre_rating.rating < 4:
            participant_stance = 'anti'
        else:  # rating == 4
            participant_stance = 'neutral'
    except Rating.DoesNotExist:
        participant_stance = 'neutral'

    # Get existing chat turns
    chat_turns = ChatTurn.objects.filter(
        participant=participant,
        dilemma=dilemma
    ).order_by('timestamp')

    return render(request, 'experiment/chat.html', {
        'participant': participant,
        'dilemma': dilemma,
        'chat_index': index,
        'total_chats': len(chat_dilemma_ids),
        'chat_turns': chat_turns,
        'participant_stance': participant_stance,
        'timer_seconds': get_timer_seconds(270),  # 4.5 minutes
        'page_name': f'chat_{index}',
    })


@never_cache
def post_rating(request, index):
    """Re-rate one dilemma at a time after chat debates."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Get dilemmas in assigned order for post-rating (different from pre-rating)
    dilemma_ids = participant.post_dilemma_order
    num_dilemmas = len(dilemma_ids)

    # Check if attention check is in this phase
    has_attention_check = participant.attention_check_phase == 'post'
    attention_check_pos = participant.attention_check_position if has_attention_check else None

    # Total items: 9 dilemmas + 1 attention check if in this phase
    total_items = num_dilemmas + 1 if has_attention_check else num_dilemmas

    # Validate index
    if index < 0 or index >= total_items:
        return redirect('experiment:debrief')

    # Determine if this index is the attention check
    is_attention_check = has_attention_check and index == attention_check_pos

    # Calculate dilemma index (adjusted for attention check position)
    if is_attention_check:
        dilemma = None
        dilemma_index = None
    elif has_attention_check and index > attention_check_pos:
        dilemma_index = index - 1
        try:
            dilemma = Dilemma.objects.get(id=dilemma_ids[dilemma_index])
        except Dilemma.DoesNotExist:
            return redirect('experiment:debrief')
    else:
        dilemma_index = index
        try:
            dilemma = Dilemma.objects.get(id=dilemma_ids[dilemma_index])
        except Dilemma.DoesNotExist:
            return redirect('experiment:debrief')

    # Server-side protection: check if already answered (prevent back-button modification)
    if is_attention_check:
        # Check if attention check was already answered
        if participant.attention_check_response is not None:
            EventLog.objects.create(
                participant=participant,
                event_type='attempted_attention_check_modification',
                page='post_rating',
                data={'index': index, 'existing_response': participant.attention_check_response}
            )
            # If they failed, send them back to failed page
            if participant.status == 'attention_failed':
                return redirect('experiment:attention_failed')
            # Otherwise skip to next item
            if index + 1 < total_items:
                return redirect('experiment:post_rating', index=index + 1)
            else:
                return redirect('experiment:debrief')
    elif dilemma:
        existing_rating = Rating.objects.filter(
            participant=participant,
            dilemma=dilemma,
            phase='post'
        ).exists()
        if existing_rating:
            # Log the attempt and skip to next item
            EventLog.objects.create(
                participant=participant,
                event_type='attempted_rating_modification',
                page='post_rating',
                data={'dilemma_id': dilemma.id, 'index': index}
            )
            # Move to next item or phase
            if index + 1 < total_items:
                return redirect('experiment:post_rating', index=index + 1)
            else:
                return redirect('experiment:debrief')

    if request.method == 'POST':
        if is_attention_check:
            # Handle attention check response (only if not already answered)
            if participant.attention_check_response is None:
                rating_value = request.POST.get('rating_attention_check')
                if rating_value:
                    rating_int = int(rating_value)
                    participant.attention_check_response = rating_int
                    participant.attention_check_passed = (rating_int == 3)

                    EventLog.objects.create(
                        participant=participant,
                        event_type='attention_check_completed',
                        page='post_rating',
                        data={
                            'response': rating_int,
                            'passed': rating_int == 3,
                            'position': index
                        }
                    )

                    # If attention check failed, end the survey immediately
                    if rating_int != 3:
                        participant.status = 'attention_failed'
                        participant.save()
                        return redirect('experiment:attention_failed')

                    participant.save()
        else:
            # Save rating for this dilemma
            rating_value = request.POST.get(f'rating_{dilemma.id}')
            if rating_value:
                # Use get_or_create to prevent rating modification
                Rating.objects.get_or_create(
                    participant=participant,
                    dilemma=dilemma,
                    phase='post',
                    defaults={'rating': int(rating_value)}
                )

        # Move to next item or to debrief
        if index + 1 < total_items:
            return redirect('experiment:post_rating', index=index + 1)
        else:
            participant.status = 'post_rating'
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='post_rating_completed',
                page='post_rating'
            )

            return redirect('experiment:debrief')

    return render(request, 'experiment/post_rating.html', {
        'participant': participant,
        'dilemma': dilemma,
        'dilemma_index': index,
        'total_dilemmas': total_items,
        'is_attention_check': is_attention_check,
        'attention_check_text': ATTENTION_CHECK_TEXT if is_attention_check else None,
        'timer_seconds': get_timer_seconds(30),
        'page_name': f'post_rating_{index}',
    })


def debrief(request):
    """Debrief page with feedback form and withdrawal option."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Build condition description and sample prompt for debrief
    condition_descriptions = {
        'neutral': 'Neutral - The AI discussed the dilemmas using ethical reasoning without explicit persuasion goals.',
        'persuade': 'Persuade - The AI was instructed to either reinforce or challenge your position on each dilemma using compelling arguments.',
        'persuade_demo': 'Persuade + Demographics - The AI was instructed to reinforce or challenge your position, and was given your demographic information (age, gender, education) to tailor its approach.',
        'persuade_info': 'Persuade + Demographics + Personality - The AI was instructed to reinforce or challenge your position, and was given both your demographic information and personality profile to tailor its approach.',
    }
    condition_description = condition_descriptions.get(participant.condition, participant.condition)

    # Get a sample dilemma to show an example prompt
    sample_prompt = None
    chat_dilemma_ids = participant.chat_dilemma_ids
    if chat_dilemma_ids:
        try:
            sample_dilemma = Dilemma.objects.get(id=chat_dilemma_ids[0])
            # Get participant's rating on this dilemma
            try:
                pre_rating = Rating.objects.get(
                    participant=participant,
                    dilemma=sample_dilemma,
                    phase='pre'
                )
                participant_rating = pre_rating.rating
            except Rating.DoesNotExist:
                participant_rating = 4

            # Get stance mode for this dilemma
            stance_assignments = participant.stance_assignments
            stance_mode = stance_assignments.get(str(sample_dilemma.id), 'opposite')

            # Determine LLM framework
            llm_framework = get_llm_framework(
                participant_rating=participant_rating,
                low_rating_framework=sample_dilemma.low_rating_framework,
                stance_mode=stance_mode
            )

            # Calculate LLM position (pro/contra the action)
            llm_position = get_llm_position(
                participant_rating=participant_rating,
                low_rating_framework=sample_dilemma.low_rating_framework,
                stance_mode=stance_mode
            )

            # Get demographics if applicable
            demographics_info = None
            if participant.condition in ['persuade_demo', 'persuade_info']:
                try:
                    demographics_info = participant.demographics.get_demographics_summary()
                except DemographicsResponse.DoesNotExist:
                    pass

            # Get personality profile if applicable
            personality_profile = None
            if participant.condition == 'persuade_info':
                try:
                    personality_profile = participant.tipi.get_personality_profile()
                except TIPIResponse.DoesNotExist:
                    pass

            # Only include position_description for counterintuitive dilemmas (Marital Affair)
            position_description = None
            if sample_dilemma.code == 'Marital Affair':
                position_description = (
                    sample_dilemma.deontological_position if llm_framework == 'deontological'
                    else sample_dilemma.utilitarian_position
                ) or None

            sample_prompt = build_system_prompt(
                condition=participant.condition,
                dilemma_text=sample_dilemma.text,
                llm_framework=llm_framework,
                llm_position=llm_position,
                stance_mode=stance_mode,
                participant_rating=participant_rating,
                personality_profile=personality_profile,
                demographics_info=demographics_info,
                position_description=position_description
            )
        except Dilemma.DoesNotExist:
            pass

    if request.method == 'POST':
        # Check for withdrawal
        if request.POST.get('withdraw') == 'yes':
            participant.status = 'withdrawn'
            participant.withdrawn = True
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='withdrawal',
                page='debrief'
            )

            return redirect('experiment:withdrawn')

        # Collect AI tools used (checkboxes)
        ai_tools = request.POST.getlist('ai_tools')
        ai_tools_other = request.POST.get('ai_tools_other', '')
        if 'other' in ai_tools and ai_tools_other:
            ai_tools = [t for t in ai_tools if t != 'other'] + [ai_tools_other]
        ai_tools_str = ', '.join(ai_tools) if ai_tools else ''

        # Handle S-TIAS scores (convert to int or None)
        def get_int_or_none(field_name):
            val = request.POST.get(field_name, '')
            return int(val) if val.isdigit() else None

        # Save debrief responses
        DebriefResponse.objects.update_or_create(
            participant=participant,
            defaults={
                # S-TIAS Trust Scale
                'stias_confident': get_int_or_none('stias_confident'),
                'stias_reliable': get_int_or_none('stias_reliable'),
                'stias_trust': get_int_or_none('stias_trust'),
                # AI usage
                'ai_usage_frequency': request.POST.get('ai_usage_frequency', ''),
                'ai_tools_used': ai_tools_str,
                'ai_usage_tasks': request.POST.get('ai_usage_tasks', ''),
                # Feedback
                'noticed_persuasion': request.POST.get('noticed_persuasion') == 'yes',
                'persuasion_description': request.POST.get('persuasion_description', ''),
                'changed_mind': request.POST.get('changed_mind') == 'yes',
                'change_description': request.POST.get('change_description', ''),
                'general_feedback': request.POST.get('general_feedback', ''),
                # Contact
                'results_email': request.POST.get('results_email', ''),
            }
        )

        participant.status = 'debrief'
        participant.save()

        EventLog.objects.create(
            participant=participant,
            event_type='debrief_completed',
            page='debrief'
        )

        return redirect('experiment:complete')

    return render(request, 'experiment/debrief.html', {
        'participant': participant,
        'condition_description': condition_description,
        'sample_prompt': sample_prompt,
        'timer_seconds': get_timer_seconds(300),  # 5 minutes
        'timer_enforce_wait': False,  # Timer is informational only
        'page_name': 'debrief',
    })


def complete(request):
    """Completion page - redirect to Prolific."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Only process completion once (avoid double counting on page refresh)
    if participant.status != 'complete':
        # Increment completion counter for pilot balancing
        CompletionCell.increment_completion(
            participant.condition,
            participant.llm_provider
        )

        # Generate completion code
        participant.completion_code = generate_completion_code(participant.id)
        participant.status = 'complete'
        participant.completed_at = timezone.now()
        participant.save()

        EventLog.objects.create(
            participant=participant,
            event_type='experiment_completed',
            page='complete'
        )

    return render(request, 'experiment/complete.html', {
        'participant': participant,
        'completion_code': participant.completion_code,
        'prolific_url': settings.PROLIFIC_COMPLETION_URL,
    })


def withdrawn(request):
    """Page shown when participant withdraws."""
    return render(request, 'experiment/withdrawn.html')


def attention_failed(request):
    """Page shown when participant fails the attention check."""
    return render(request, 'experiment/attention_failed.html')


def connection_error(request):
    """Page shown when LLM connection fails (503 error)."""
    return render(request, 'experiment/connection_error.html', status=503)


# API Views

@require_http_methods(["POST"])
def chat_send(request):
    """Handle chat message and stream LLM response."""
    participant = get_or_create_participant(request)
    if not participant:
        return JsonResponse({'error': 'No participant found'}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        dilemma_id = data.get('dilemma_id')
        chat_history = data.get('history', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_message or not dilemma_id:
        return JsonResponse({'error': 'Missing message or dilemma_id'}, status=400)

    try:
        dilemma = Dilemma.objects.get(id=dilemma_id)
    except Dilemma.DoesNotExist:
        return JsonResponse({'error': 'Dilemma not found'}, status=404)

    # Add user message to history for LLM context
    chat_history.append({'sender': 'user', 'text': user_message})

    # Build system prompt
    try:
        pre_rating = Rating.objects.get(
            participant=participant,
            dilemma=dilemma,
            phase='pre'
        )
        participant_rating = pre_rating.rating
    except Rating.DoesNotExist:
        # This shouldn't happen - participant should have rated before chat
        logger.warning(
            f"Missing pre-rating: participant={participant.id}, dilemma={dilemma.id}. "
            f"Defaulting to neutral (4)."
        )
        EventLog.objects.create(
            participant=participant,
            event_type='missing_pre_rating',
            page='chat_send',
            data={'dilemma_id': dilemma.id}
        )
        participant_rating = 4

    # Get stance mode from participant's stance assignments
    stance_assignments = participant.stance_assignments
    stance_mode = stance_assignments.get(str(dilemma.id), 'opposite')

    llm_framework = get_llm_framework(
        participant_rating=participant_rating,
        low_rating_framework=dilemma.low_rating_framework,
        stance_mode=stance_mode
    )

    # Calculate LLM position (pro/contra the action)
    llm_position = get_llm_position(
        participant_rating=participant_rating,
        low_rating_framework=dilemma.low_rating_framework,
        stance_mode=stance_mode
    )

    # Get demographics if applicable
    demographics_info = None
    if participant.condition in ['persuade_demo', 'persuade_info']:
        try:
            demographics_info = participant.demographics.get_demographics_summary()
        except DemographicsResponse.DoesNotExist:
            logger.warning(f"Missing demographics for participant={participant.id} in {participant.condition} condition")

    # Get personality profile if applicable
    personality_profile = None
    if participant.condition == 'persuade_info':
        try:
            personality_profile = participant.tipi.get_personality_profile()
        except TIPIResponse.DoesNotExist:
            logger.warning(f"Missing TIPI for participant={participant.id} in persuade_info condition")

    # Only include position_description for counterintuitive dilemmas (Marital Affair)
    position_description = None
    if dilemma.code == 'Marital Affair':
        position_description = (
            dilemma.deontological_position if llm_framework == 'deontological'
            else dilemma.utilitarian_position
        ) or None

    system_prompt = build_system_prompt(
        condition=participant.condition,
        dilemma_text=dilemma.text,
        llm_framework=llm_framework,
        llm_position=llm_position,
        stance_mode=stance_mode,
        participant_rating=participant_rating,
        personality_profile=personality_profile,
        demographics_info=demographics_info,
        position_description=position_description
    )

    # Log the system prompt (create or update to avoid duplicates)
    SystemPromptLog.objects.get_or_create(
        participant=participant,
        dilemma=dilemma,
        defaults={
            'prompt_text': system_prompt,
            'condition': participant.condition,
            'llm_framework': llm_framework,
            'stance_mode': stance_mode,
            'llm_position': llm_position,
            'personality_profile': personality_profile or '',
        }
    )

    # Get LLM client
    llm_client = get_llm_client(participant.llm_provider)

    def generate():
        full_response = []
        try:
            for chunk in llm_client.stream_response(system_prompt, chat_history):
                full_response.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@require_http_methods(["POST"])
def chat_init(request):
    """Get initial AI message to start the conversation."""
    participant = get_or_create_participant(request)
    if not participant:
        return JsonResponse({'error': 'No participant found'}, status=400)

    try:
        data = json.loads(request.body)
        dilemma_id = data.get('dilemma_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not dilemma_id:
        return JsonResponse({'error': 'Missing dilemma_id'}, status=400)

    try:
        dilemma = Dilemma.objects.get(id=dilemma_id)
    except Dilemma.DoesNotExist:
        return JsonResponse({'error': 'Dilemma not found'}, status=404)

    # Check if there's already chat history for this dilemma in database
    existing_turns = ChatTurn.objects.filter(
        participant=participant,
        dilemma=dilemma
    ).exists()

    if existing_turns:
        return JsonResponse({'already_started': True})

    # Get participant's pre-rating and determine LLM's ethical framework
    try:
        pre_rating = Rating.objects.get(
            participant=participant,
            dilemma=dilemma,
            phase='pre'
        )
        participant_rating = pre_rating.rating
    except Rating.DoesNotExist:
        # This shouldn't happen - participant should have rated before chat
        logger.warning(
            f"Missing pre-rating: participant={participant.id}, dilemma={dilemma.id}. "
            f"Defaulting to neutral (4)."
        )
        EventLog.objects.create(
            participant=participant,
            event_type='missing_pre_rating',
            page='chat_init',
            data={'dilemma_id': dilemma.id}
        )
        participant_rating = 4

    # Get stance mode from participant's stance assignments
    stance_assignments = participant.stance_assignments
    stance_mode = stance_assignments.get(str(dilemma.id), 'opposite')

    llm_framework = get_llm_framework(
        participant_rating=participant_rating,
        low_rating_framework=dilemma.low_rating_framework,
        stance_mode=stance_mode
    )

    # Calculate LLM position (pro/contra the action)
    llm_position = get_llm_position(
        participant_rating=participant_rating,
        low_rating_framework=dilemma.low_rating_framework,
        stance_mode=stance_mode
    )

    # Get demographics if applicable
    demographics_info = None
    if participant.condition in ['persuade_demo', 'persuade_info']:
        try:
            demographics_info = participant.demographics.get_demographics_summary()
        except DemographicsResponse.DoesNotExist:
            logger.warning(f"Missing demographics for participant={participant.id} in {participant.condition} condition")

    # Get personality profile if needed
    personality_profile = None
    if participant.condition == 'persuade_info':
        try:
            personality_profile = participant.tipi.get_personality_profile()
        except TIPIResponse.DoesNotExist:
            logger.warning(f"Missing TIPI for participant={participant.id} in persuade_info condition")

    # Only include position_description for counterintuitive dilemmas (Marital Affair)
    position_description = None
    if dilemma.code == 'Marital Affair':
        position_description = (
            dilemma.deontological_position if llm_framework == 'deontological'
            else dilemma.utilitarian_position
        ) or None

    # Build system prompt
    system_prompt = build_system_prompt(
        condition=participant.condition,
        dilemma_text=dilemma.text,
        llm_framework=llm_framework,
        llm_position=llm_position,
        stance_mode=stance_mode,
        participant_rating=participant_rating,
        personality_profile=personality_profile,
        demographics_info=demographics_info,
        position_description=position_description
    )

    # Log the system prompt (create or update to avoid duplicates)
    SystemPromptLog.objects.get_or_create(
        participant=participant,
        dilemma=dilemma,
        defaults={
            'prompt_text': system_prompt,
            'condition': participant.condition,
            'llm_framework': llm_framework,
            'stance_mode': stance_mode,
            'llm_position': llm_position,
            'personality_profile': personality_profile or '',
        }
    )

    # Get LLM client
    llm_client = get_llm_client(participant.llm_provider)

    # Initial prompt to start conversation
    initial_messages = [{'sender': 'user', 'text': 'Please share your initial thoughts on this dilemma.'}]

    def generate():
        full_response = []
        try:
            for chunk in llm_client.stream_response(system_prompt, initial_messages):
                full_response.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
@require_http_methods(["POST"])
def chat_save(request):
    """Save all chat messages to database when leaving chat page."""
    participant = get_or_create_participant(request)
    if not participant:
        return JsonResponse({'error': 'No participant found'}, status=400)

    try:
        data = json.loads(request.body)
        dilemma_id = data.get('dilemma_id')
        messages = data.get('messages', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not dilemma_id:
        return JsonResponse({'error': 'Missing dilemma_id'}, status=400)

    if not messages:
        return JsonResponse({'status': 'no_messages'})

    try:
        dilemma = Dilemma.objects.get(id=dilemma_id)
    except Dilemma.DoesNotExist:
        return JsonResponse({'error': 'Dilemma not found'}, status=404)

    # Count existing messages to avoid duplicates - only save new ones
    existing_count = ChatTurn.objects.filter(
        participant=participant,
        dilemma=dilemma
    ).count()

    # Only save messages beyond what's already saved
    new_messages = messages[existing_count:]

    if not new_messages:
        return JsonResponse({'status': 'already_saved', 'existing_count': existing_count})

    # Save new messages to database
    for msg in new_messages:
        # Parse timestamp from client or use current time as fallback
        if msg.get('timestamp'):
            try:
                ts = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                ts = timezone.now()
        else:
            ts = timezone.now()

        ChatTurn.objects.create(
            participant=participant,
            dilemma=dilemma,
            sender=msg['sender'],
            text=msg['text'],
            timestamp=ts
        )

    return JsonResponse({'status': 'saved', 'count': len(new_messages), 'total': len(messages)})


@require_http_methods(["POST"])
def log_event(request):
    """Log client-side events."""
    participant = get_or_create_participant(request)
    if not participant:
        return JsonResponse({'error': 'No participant found'}, status=400)

    try:
        data = json.loads(request.body)
        event_type = data.get('event_type', 'unknown')
        page = data.get('page', '')
        event_data = data.get('data', {})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    EventLog.objects.create(
        participant=participant,
        event_type=event_type,
        page=page,
        data=event_data
    )

    return JsonResponse({'status': 'ok'})


@require_http_methods(["POST"])
def timer_expired(request):
    """Handle timer expiration - return next URL."""
    participant = get_or_create_participant(request)
    if not participant:
        return JsonResponse({'error': 'No participant found'}, status=400)

    try:
        data = json.loads(request.body)
        current_page = data.get('page', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Log timer expiration
    EventLog.objects.create(
        participant=participant,
        event_type='timer_expired',
        page=current_page
    )

    # Determine next URL based on current page
    next_url = '/'
    num_dilemmas = len(participant.pre_dilemma_order)  # Same count for pre and post
    total_chats = len(participant.chat_dilemma_ids)

    # Calculate total items for each rating phase (including attention check if applicable)
    total_pre_items = num_dilemmas + 1 if participant.attention_check_phase == 'pre' else num_dilemmas
    total_post_items = num_dilemmas + 1 if participant.attention_check_phase == 'post' else num_dilemmas

    if current_page == 'demographics':
        next_url = '/tipi/'
    elif current_page == 'tipi':
        next_url = '/pre-rating/0/'
    elif current_page.startswith('pre_rating_'):
        # Extract index from pre_rating_0, pre_rating_1, etc.
        try:
            index = int(current_page.split('_')[-1])
            if index + 1 < total_pre_items:
                next_url = f'/pre-rating/{index + 1}/'
            else:
                next_url = '/chat/0/'
        except (ValueError, IndexError):
            next_url = '/chat/0/'
    elif current_page.startswith('chat_'):
        # Extract index from chat_0, chat_1, etc.
        try:
            index = int(current_page.split('_')[1])
            if index + 1 < total_chats:
                next_url = f'/chat/{index + 1}/'
            else:
                next_url = '/post-rating/0/'
        except (ValueError, IndexError):
            next_url = '/post-rating/0/'
    elif current_page.startswith('post_rating_'):
        # Extract index from post_rating_0, post_rating_1, etc.
        try:
            index = int(current_page.split('_')[-1])
            if index + 1 < total_post_items:
                next_url = f'/post-rating/{index + 1}/'
            else:
                next_url = '/debrief/'
        except (ValueError, IndexError):
            next_url = '/debrief/'
    elif current_page == 'debrief':
        next_url = '/complete/'

    return JsonResponse({'next_url': next_url})
