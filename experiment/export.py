"""
Export functionality for experiment data.
Supports JSON and CSV formats.
"""
import csv
import io
import json
from datetime import datetime

from .models import (
    Participant, Dilemma, TIPIResponse, Rating, ChatTurn,
    EventLog, DebriefResponse, SystemPromptLog, DemographicsResponse,
    get_attention_check_text, ATTENTION_CHECK_RATING_PRE, ATTENTION_CHECK_RATING_POST
)


def get_participant_data(participant_id):
    """
    Gather all data for a single participant.
    Returns a dictionary with all related data.
    """
    try:
        participant = Participant.objects.get(id=participant_id)
    except Participant.DoesNotExist:
        return None

    data = {
        'participant': {
            'id': participant.id,
            'session_key': participant.session_key,
            'condition': participant.condition,
            'llm_provider': participant.llm_provider,
            'status': participant.status,
            'withdrawn': participant.withdrawn,
            'created_at': participant.created_at.isoformat() if participant.created_at else None,
            'completed_at': participant.completed_at.isoformat() if participant.completed_at else None,
            'chat_dilemma_ids': participant.chat_dilemma_ids,
            'pre_dilemma_order': participant.pre_dilemma_order,
            'post_dilemma_order': participant.post_dilemma_order,
            'current_chat_index': participant.current_chat_index,
            'stance_assignments': participant.stance_assignments,
            'stance_combination_used': participant.stance_combination_used,
            'koerner_chat_cost_category': participant.koerner_chat_cost_category,
            'attention_check_position_pre': participant.attention_check_position_pre,
            'attention_check_response_pre': participant.attention_check_response_pre,
            'attention_check_correct_pre': ATTENTION_CHECK_RATING_PRE,
            'attention_check_text_pre': get_attention_check_text('pre'),
            'attention_check_position_post': participant.attention_check_position_post,
            'attention_check_response_post': participant.attention_check_response_post,
            'attention_check_correct_post': ATTENTION_CHECK_RATING_POST,
            'attention_check_text_post': get_attention_check_text('post'),
        }
    }

    # TIPI responses
    try:
        tipi = participant.tipi
        data['tipi'] = {
            'raw_items': {
                'item_1': tipi.item_1,
                'item_2': tipi.item_2,
                'item_3': tipi.item_3,
                'item_4': tipi.item_4,
                'item_5': tipi.item_5,
                'item_6': tipi.item_6,
                'item_7': tipi.item_7,
                'item_8': tipi.item_8,
                'item_9': tipi.item_9,
                'item_10': tipi.item_10,
            },
            'big_five': {
                'extraversion': tipi.extraversion,
                'agreeableness': tipi.agreeableness,
                'conscientiousness': tipi.conscientiousness,
                'emotional_stability': tipi.emotional_stability,
                'openness': tipi.openness,
            },
            'personality_profile': tipi.get_personality_profile(),
            'created_at': tipi.created_at.isoformat() if tipi.created_at else None,
        }
    except TIPIResponse.DoesNotExist:
        data['tipi'] = None

    # Demographics (collected early in flow)
    try:
        demo = participant.demographics
        data['demographics'] = {
            'age': demo.age,
            'gender': demo.gender,
            'gender_other': demo.gender_other,
            'education': demo.education,
            'native_english': demo.native_english,
            'created_at': demo.created_at.isoformat() if demo.created_at else None,
        }
    except DemographicsResponse.DoesNotExist:
        data['demographics'] = None

    # Ratings (pre and post)
    ratings = Rating.objects.filter(participant=participant).select_related('dilemma')
    data['ratings'] = [
        {
            'dilemma_code': r.dilemma.code,
            'dilemma_id': r.dilemma.id,
            'phase': r.phase,
            'rating': r.rating,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }
        for r in ratings
    ]

    # Chat transcripts
    chat_turns = ChatTurn.objects.filter(participant=participant).select_related('dilemma')
    chats_by_dilemma = {}
    for turn in chat_turns:
        dilemma_code = turn.dilemma.code
        if dilemma_code not in chats_by_dilemma:
            chats_by_dilemma[dilemma_code] = {
                'dilemma_id': turn.dilemma.id,
                'dilemma_code': dilemma_code,
                'turns': []
            }
        chats_by_dilemma[dilemma_code]['turns'].append({
            'sender': turn.sender,
            'text': turn.text,
            'timestamp': turn.timestamp.isoformat() if turn.timestamp else None,
        })
    data['chats'] = list(chats_by_dilemma.values())

    # System prompts
    system_prompts = SystemPromptLog.objects.filter(participant=participant).select_related('dilemma')
    data['system_prompts'] = [
        {
            'dilemma_code': sp.dilemma.code,
            'dilemma_id': sp.dilemma.id,
            'condition': sp.condition,
            'llm_framework': sp.llm_framework,
            'stance_mode': sp.stance_mode,
            'llm_position': sp.llm_position,
            'personality_profile': sp.personality_profile,
            'prompt_text': sp.prompt_text,
            'created_at': sp.created_at.isoformat() if sp.created_at else None,
        }
        for sp in system_prompts
    ]

    # Event logs
    events = EventLog.objects.filter(participant=participant)
    data['events'] = [
        {
            'event_type': e.event_type,
            'page': e.page,
            'data': e.data,
            'timestamp': e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]

    # Debrief response
    try:
        debrief = participant.debrief
        data['debrief'] = {
            # S-TIAS Trust Scale
            'stias_confident': debrief.stias_confident,
            'stias_reliable': debrief.stias_reliable,
            'stias_trust': debrief.stias_trust,
            'stias_average': debrief.stias_average,
            # AI usage
            'ai_usage_frequency': debrief.ai_usage_frequency,
            'ai_tools_used': debrief.ai_tools_used,
            'ai_usage_tasks': debrief.ai_usage_tasks,
            # Feedback
            'noticed_persuasion': debrief.noticed_persuasion,
            'persuasion_description': debrief.persuasion_description,
            'changed_mind': debrief.changed_mind,
            'change_description': debrief.change_description,
            'general_feedback': debrief.general_feedback,
            # Contact
            'results_email': debrief.results_email,
            'created_at': debrief.created_at.isoformat() if debrief.created_at else None,
        }
    except DebriefResponse.DoesNotExist:
        data['debrief'] = None

    return data


def export_participants_json(participant_ids):
    """
    Export participant data as JSON.
    Returns JSON string.
    """
    export_data = {
        'export_timestamp': datetime.now().isoformat(),
        'participant_count': len(participant_ids),
        'participants': []
    }

    for pid in participant_ids:
        pdata = get_participant_data(pid)
        if pdata:
            export_data['participants'].append(pdata)

    return json.dumps(export_data, indent=2, ensure_ascii=False)


def export_participants_csv(participant_ids):
    """
    Export participant data as CSV.
    Flattens the data structure into a single row per participant.
    Returns CSV string.
    """
    output = io.StringIO()

    # Define all columns
    fieldnames = [
        # Participant info
        'participant_id', 'condition', 'llm_provider',
        'status', 'withdrawn', 'created_at', 'completed_at',

        # Stance assignment info
        'stance_combination_used', 'koerner_chat_cost_category',
        'stance_assignments_json',

        # Attention check info
        'attention_check_position_pre', 'attention_check_response_pre',
        'attention_check_correct_pre', 'attention_check_text_pre',
        'attention_check_position_post', 'attention_check_response_post',
        'attention_check_correct_post', 'attention_check_text_post',

        # Demographics (collected early in flow)
        'demographics_age', 'demographics_gender', 'demographics_gender_other',
        'demographics_education', 'demographics_native_english',

        # TIPI raw items
        'tipi_item_1', 'tipi_item_2', 'tipi_item_3', 'tipi_item_4', 'tipi_item_5',
        'tipi_item_6', 'tipi_item_7', 'tipi_item_8', 'tipi_item_9', 'tipi_item_10',

        # TIPI Big Five scores
        'tipi_extraversion', 'tipi_agreeableness', 'tipi_conscientiousness',
        'tipi_emotional_stability', 'tipi_openness',

        # Debrief - S-TIAS Trust Scale
        'debrief_stias_confident', 'debrief_stias_reliable', 'debrief_stias_trust', 'debrief_stias_average',

        # Debrief - AI usage
        'debrief_ai_usage_frequency', 'debrief_ai_tools_used', 'debrief_ai_usage_tasks',

        # Debrief - Feedback
        'debrief_noticed_persuasion', 'debrief_persuasion_description',
        'debrief_changed_mind', 'debrief_change_description', 'debrief_general_feedback',

        # Debrief - Contact
        'debrief_results_email',

        # We'll add dynamic columns for ratings and chats
    ]

    # Get all dilemma codes for dynamic columns
    dilemmas = list(Dilemma.objects.values_list('code', flat=True))
    for code in dilemmas:
        fieldnames.append(f'rating_pre_{code}')
        fieldnames.append(f'rating_post_{code}')
        fieldnames.append(f'chat_turn_count_{code}')
        fieldnames.append(f'system_prompt_{code}')

    # Add event count and chat transcript columns
    fieldnames.extend(['event_count', 'chat_transcripts_json', 'system_prompts_json', 'events_json'])

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    for pid in participant_ids:
        pdata = get_participant_data(pid)
        if not pdata:
            continue

        p = pdata['participant']
        row = {
            'participant_id': p['id'],
            'condition': p['condition'],
            'llm_provider': p['llm_provider'],
            'status': p['status'],
            'withdrawn': p['withdrawn'],
            'created_at': p['created_at'],
            'completed_at': p['completed_at'],
            'stance_combination_used': p.get('stance_combination_used'),
            'koerner_chat_cost_category': p.get('koerner_chat_cost_category', ''),
            'stance_assignments_json': json.dumps(p.get('stance_assignments', {}), ensure_ascii=False),
            'attention_check_position_pre': p.get('attention_check_position_pre'),
            'attention_check_response_pre': p.get('attention_check_response_pre'),
            'attention_check_correct_pre': p.get('attention_check_correct_pre'),
            'attention_check_text_pre': p.get('attention_check_text_pre', ''),
            'attention_check_position_post': p.get('attention_check_position_post'),
            'attention_check_response_post': p.get('attention_check_response_post'),
            'attention_check_correct_post': p.get('attention_check_correct_post'),
            'attention_check_text_post': p.get('attention_check_text_post', ''),
        }

        # Demographics data (collected early in flow)
        if pdata.get('demographics'):
            demo = pdata['demographics']
            row['demographics_age'] = demo.get('age')
            row['demographics_gender'] = demo.get('gender', '')
            row['demographics_gender_other'] = demo.get('gender_other', '')
            row['demographics_education'] = demo.get('education', '')
            row['demographics_native_english'] = demo.get('native_english')

        # TIPI data
        if pdata['tipi']:
            tipi = pdata['tipi']
            for i in range(1, 11):
                row[f'tipi_item_{i}'] = tipi['raw_items'][f'item_{i}']
            row['tipi_extraversion'] = tipi['big_five']['extraversion']
            row['tipi_agreeableness'] = tipi['big_five']['agreeableness']
            row['tipi_conscientiousness'] = tipi['big_five']['conscientiousness']
            row['tipi_emotional_stability'] = tipi['big_five']['emotional_stability']
            row['tipi_openness'] = tipi['big_five']['openness']

        # Debrief data
        if pdata['debrief']:
            d = pdata['debrief']
            # S-TIAS Trust Scale
            row['debrief_stias_confident'] = d.get('stias_confident')
            row['debrief_stias_reliable'] = d.get('stias_reliable')
            row['debrief_stias_trust'] = d.get('stias_trust')
            row['debrief_stias_average'] = d.get('stias_average')
            # AI usage
            row['debrief_ai_usage_frequency'] = d.get('ai_usage_frequency', '')
            row['debrief_ai_tools_used'] = d.get('ai_tools_used', '')
            row['debrief_ai_usage_tasks'] = d.get('ai_usage_tasks', '')
            # Feedback
            row['debrief_noticed_persuasion'] = d.get('noticed_persuasion')
            row['debrief_persuasion_description'] = d.get('persuasion_description', '')
            row['debrief_changed_mind'] = d.get('changed_mind')
            row['debrief_change_description'] = d.get('change_description', '')
            row['debrief_general_feedback'] = d.get('general_feedback', '')
            # Contact
            row['debrief_results_email'] = d.get('results_email', '')

        # Ratings by dilemma
        for rating in pdata['ratings']:
            code = rating['dilemma_code']
            phase = rating['phase']
            row[f'rating_{phase}_{code}'] = rating['rating']

        # Chat turn counts and system prompts by dilemma
        for chat in pdata['chats']:
            code = chat['dilemma_code']
            row[f'chat_turn_count_{code}'] = len(chat['turns'])

        for sp in pdata['system_prompts']:
            code = sp['dilemma_code']
            row[f'system_prompt_{code}'] = sp['llm_framework']

        # Event count and JSON fields for detailed data
        row['event_count'] = len(pdata['events'])
        row['chat_transcripts_json'] = json.dumps(pdata['chats'], ensure_ascii=False)
        row['system_prompts_json'] = json.dumps(pdata['system_prompts'], ensure_ascii=False)
        row['events_json'] = json.dumps(pdata['events'], ensure_ascii=False)

        writer.writerow(row)

    return output.getvalue()
