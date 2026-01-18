import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from .models import (
    Participant, Dilemma, TIPIResponse, Rating, ChatTurn, EventLog, DebriefResponse
)
from .llm import get_llm_client, build_system_prompt


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

        # Random condition assignment
        condition = random.choice(['neutral', 'persuade', 'persuade_info'])

        # Random LLM provider assignment
        llm_provider = random.choice(['openai', 'anthropic', 'qwen'])

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
        return redirect('experiment:tipi')
    elif status == 'tipi':
        return redirect('experiment:pre_rating')
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
    else:
        return redirect('experiment:landing')


def consent(request):
    """Display consent form and update status on agreement."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    if request.method == 'POST':
        if request.POST.get('consent') == 'agree':
            participant.status = 'consent'
            participant.save()

            EventLog.objects.create(
                participant=participant,
                event_type='consent_given',
                page='consent'
            )

            return redirect('experiment:tipi')
        else:
            # Did not consent - withdraw
            participant.status = 'withdrawn'
            participant.withdrawn = True
            participant.save()
            return redirect('experiment:withdrawn')

    return render(request, 'experiment/consent.html', {
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

            return redirect('experiment:pre_rating')

    return render(request, 'experiment/tipi.html', {
        'participant': participant,
        'tipi_items': tipi_items,
        'timer_seconds': 120,  # 2 minutes
    })


def pre_rating(request):
    """Rate all 8 dilemmas before chat debates."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Get dilemmas in assigned order
    dilemma_ids = participant.all_dilemma_order
    dilemmas = []
    for did in dilemma_ids:
        try:
            dilemmas.append(Dilemma.objects.get(id=did))
        except Dilemma.DoesNotExist:
            pass

    if request.method == 'POST':
        # Save all ratings
        for dilemma in dilemmas:
            rating_value = request.POST.get(f'rating_{dilemma.id}')
            if rating_value:
                Rating.objects.update_or_create(
                    participant=participant,
                    dilemma=dilemma,
                    phase='pre',
                    defaults={'rating': int(rating_value)}
                )

        participant.status = 'pre_rating'
        participant.save()

        EventLog.objects.create(
            participant=participant,
            event_type='pre_rating_completed',
            page='pre_rating'
        )

        return redirect('experiment:chat', index=0)

    return render(request, 'experiment/pre_rating.html', {
        'participant': participant,
        'dilemmas': dilemmas,
        'timer_seconds': 420,  # 7 minutes
    })


def chat(request, index):
    """Chat interface for a specific dilemma."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Validate index
    chat_dilemma_ids = participant.chat_dilemma_ids
    if index < 0 or index >= len(chat_dilemma_ids):
        return redirect('experiment:post_rating')

    # Get current dilemma
    try:
        dilemma = Dilemma.objects.get(id=chat_dilemma_ids[index])
    except Dilemma.DoesNotExist:
        return redirect('experiment:post_rating')

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
        participant_stance = 'pro' if pre_rating.rating >= 4 else 'anti'
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
        'timer_seconds': 300,  # 5 minutes
    })


def post_rating(request):
    """Re-rate all 8 dilemmas after chat debates."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Get dilemmas in assigned order
    dilemma_ids = participant.all_dilemma_order
    dilemmas = []
    for did in dilemma_ids:
        try:
            dilemmas.append(Dilemma.objects.get(id=did))
        except Dilemma.DoesNotExist:
            pass

    if request.method == 'POST':
        # Save all ratings
        for dilemma in dilemmas:
            rating_value = request.POST.get(f'rating_{dilemma.id}')
            if rating_value:
                Rating.objects.update_or_create(
                    participant=participant,
                    dilemma=dilemma,
                    phase='post',
                    defaults={'rating': int(rating_value)}
                )

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
        'dilemmas': dilemmas,
        'timer_seconds': 300,  # 5 minutes
    })


def debrief(request):
    """Debrief page with feedback form and withdrawal option."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

    # Build condition description and sample prompt for debrief
    condition_descriptions = {
        'neutral': 'Neutral - The AI presented counterarguments using standard ethical reasoning without explicit persuasion goals.',
        'persuade': 'Persuade - The AI was instructed to actively persuade you to change your moral judgment using compelling arguments.',
        'persuade_info': 'Persuade + Personality - The AI was instructed to persuade you and was given your personality profile to tailor its approach.',
    }
    condition_description = condition_descriptions.get(participant.condition, participant.condition)

    # Get a sample dilemma to show an example prompt
    sample_prompt = None
    chat_dilemma_ids = participant.chat_dilemma_ids
    if chat_dilemma_ids:
        try:
            sample_dilemma = Dilemma.objects.get(id=chat_dilemma_ids[0])
            # Get participant's stance on this dilemma
            try:
                pre_rating = Rating.objects.get(
                    participant=participant,
                    dilemma=sample_dilemma,
                    phase='pre'
                )
                participant_stance = 'pro' if pre_rating.rating >= 4 else 'anti'
            except Rating.DoesNotExist:
                participant_stance = 'neutral'

            # Get personality profile if applicable
            personality_profile = None
            if participant.condition == 'persuade_info':
                try:
                    personality_profile = participant.tipi.get_personality_profile()
                except TIPIResponse.DoesNotExist:
                    pass

            sample_prompt = build_system_prompt(
                condition=participant.condition,
                dilemma_text=sample_dilemma.text,
                participant_stance=participant_stance,
                personality_profile=personality_profile
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

        # Save debrief responses
        DebriefResponse.objects.update_or_create(
            participant=participant,
            defaults={
                'noticed_persuasion': request.POST.get('noticed_persuasion') == 'yes',
                'persuasion_description': request.POST.get('persuasion_description', ''),
                'changed_mind': request.POST.get('changed_mind') == 'yes',
                'change_description': request.POST.get('change_description', ''),
                'general_feedback': request.POST.get('general_feedback', ''),
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
        'timer_seconds': 300,  # 5 minutes
    })


def complete(request):
    """Completion page - redirect to Prolific."""
    participant = get_or_create_participant(request)
    if not participant:
        return redirect('experiment:landing')

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
        'prolific_url': settings.PROLIFIC_COMPLETION_URL,
    })


def withdrawn(request):
    """Page shown when participant withdraws."""
    return render(request, 'experiment/withdrawn.html')


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
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_message or not dilemma_id:
        return JsonResponse({'error': 'Missing message or dilemma_id'}, status=400)

    try:
        dilemma = Dilemma.objects.get(id=dilemma_id)
    except Dilemma.DoesNotExist:
        return JsonResponse({'error': 'Dilemma not found'}, status=404)

    # Save user message
    ChatTurn.objects.create(
        participant=participant,
        dilemma=dilemma,
        sender='user',
        text=user_message
    )

    # Get chat history
    chat_history = list(ChatTurn.objects.filter(
        participant=participant,
        dilemma=dilemma
    ).order_by('timestamp').values('sender', 'text'))

    # Get participant's pre-rating stance
    try:
        pre_rating = Rating.objects.get(
            participant=participant,
            dilemma=dilemma,
            phase='pre'
        )
        participant_stance = 'pro' if pre_rating.rating >= 4 else 'anti'
    except Rating.DoesNotExist:
        participant_stance = 'neutral'

    # Get personality profile if needed
    personality_profile = None
    if participant.condition == 'persuade_info':
        try:
            personality_profile = participant.tipi.get_personality_profile()
        except TIPIResponse.DoesNotExist:
            pass

    # Build system prompt
    system_prompt = build_system_prompt(
        condition=participant.condition,
        dilemma_text=dilemma.text,
        participant_stance=participant_stance,
        personality_profile=personality_profile
    )

    # Get LLM client
    llm_client = get_llm_client(participant.llm_provider)

    def generate():
        full_response = []
        try:
            for chunk in llm_client.stream_response(system_prompt, chat_history):
                full_response.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Save AI response
            ai_response = ''.join(full_response)
            ChatTurn.objects.create(
                participant=participant,
                dilemma=dilemma,
                sender='ai',
                text=ai_response
            )

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

    if current_page == 'tipi':
        next_url = '/pre-rating/'
    elif current_page == 'pre_rating':
        next_url = '/chat/0/'
    elif current_page.startswith('chat_'):
        # Extract index from chat_0, chat_1, etc.
        try:
            index = int(current_page.split('_')[1])
            if index < 3:
                next_url = f'/chat/{index + 1}/'
            else:
                next_url = '/post-rating/'
        except (ValueError, IndexError):
            next_url = '/post-rating/'
    elif current_page == 'post_rating':
        next_url = '/debrief/'
    elif current_page == 'debrief':
        next_url = '/complete/'

    return JsonResponse({'next_url': next_url})
