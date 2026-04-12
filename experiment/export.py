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
    EventLog, DebriefResponse, SystemPromptLog
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
            'prolific_id': participant.prolific_id,
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
            'nonmoral_dilemma_id': participant.nonmoral_dilemma_id,
            'koerner_chat_cost_category': participant.koerner_chat_cost_category,
            'attention_check_phase': participant.attention_check_phase,
            'attention_check_position': participant.attention_check_position,
            'attention_check_passed': participant.attention_check_passed,
            'attention_check_response': participant.attention_check_response,
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
            # Demographics
            'age': debrief.age,
            'gender': debrief.gender,
            'gender_other': debrief.gender_other,
            'education': debrief.education,
            'native_english': debrief.native_english,
            # AI trust and usage
            'ai_trust': debrief.ai_trust,
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
        'participant_id', 'prolific_id', 'condition', 'llm_provider',
        'status', 'withdrawn', 'created_at', 'completed_at',

        # Stance assignment info
        'stance_combination_used', 'nonmoral_dilemma_id', 'koerner_chat_cost_category',
        'stance_assignments_json',

        # Attention check info
        'attention_check_phase', 'attention_check_position',
        'attention_check_passed', 'attention_check_response',

        # TIPI raw items
        'tipi_item_1', 'tipi_item_2', 'tipi_item_3', 'tipi_item_4', 'tipi_item_5',
        'tipi_item_6', 'tipi_item_7', 'tipi_item_8', 'tipi_item_9', 'tipi_item_10',

        # TIPI Big Five scores
        'tipi_extraversion', 'tipi_agreeableness', 'tipi_conscientiousness',
        'tipi_emotional_stability', 'tipi_openness',

        # Debrief - Demographics
        'debrief_age', 'debrief_gender', 'debrief_gender_other', 'debrief_education', 'debrief_native_english',

        # Debrief - AI trust and usage
        'debrief_ai_trust', 'debrief_ai_usage_frequency', 'debrief_ai_tools_used', 'debrief_ai_usage_tasks',

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
            'prolific_id': p['prolific_id'],
            'condition': p['condition'],
            'llm_provider': p['llm_provider'],
            'status': p['status'],
            'withdrawn': p['withdrawn'],
            'created_at': p['created_at'],
            'completed_at': p['completed_at'],
            'stance_combination_used': p.get('stance_combination_used'),
            'nonmoral_dilemma_id': p.get('nonmoral_dilemma_id'),
            'koerner_chat_cost_category': p.get('koerner_chat_cost_category', ''),
            'stance_assignments_json': json.dumps(p.get('stance_assignments', {}), ensure_ascii=False),
            'attention_check_phase': p.get('attention_check_phase', ''),
            'attention_check_position': p.get('attention_check_position'),
            'attention_check_passed': p.get('attention_check_passed'),
            'attention_check_response': p.get('attention_check_response'),
        }

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
            # Demographics
            row['debrief_age'] = d.get('age')
            row['debrief_gender'] = d.get('gender', '')
            row['debrief_gender_other'] = d.get('gender_other', '')
            row['debrief_education'] = d.get('education', '')
            row['debrief_native_english'] = d.get('native_english')
            # AI trust and usage
            row['debrief_ai_trust'] = d.get('ai_trust', '')
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
