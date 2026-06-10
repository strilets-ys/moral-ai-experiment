import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse

from .models import (
    Dilemma, Participant, TIPIResponse, Rating, ChatTurn, EventLog, DebriefResponse
)
from .llm import build_system_prompt, get_llm_client


class DilemmaModelTest(TestCase):
    """Tests for the Dilemma model."""

    def test_create_dilemma(self):
        """Test creating a dilemma."""
        dilemma = Dilemma.objects.create(
            code='test_dilemma',
            text='This is a test moral dilemma about a difficult situation.'
        )
        self.assertEqual(dilemma.code, 'test_dilemma')
        self.assertEqual(str(dilemma), 'test_dilemma')

    def test_dilemma_default_labels(self):
        """Test that default labels are set correctly."""
        dilemma = Dilemma.objects.create(
            code='test',
            text='Test dilemma text'
        )
        self.assertEqual(dilemma.pro_action_label, 'Action is morally acceptable')
        self.assertEqual(dilemma.anti_action_label, 'Action is morally wrong')

    def test_dilemma_code_unique(self):
        """Test that dilemma codes must be unique."""
        Dilemma.objects.create(code='unique', text='First dilemma')
        with self.assertRaises(Exception):
            Dilemma.objects.create(code='unique', text='Second dilemma')


class ParticipantModelTest(TestCase):
    """Tests for the Participant model."""

    def setUp(self):
        """Set up test dilemmas."""
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i} text')

    def test_create_participant(self):
        """Test creating a participant."""
        participant = Participant.objects.create(
            session_key='test_session_123',
            condition='neutral',
            llm_provider='openai'
        )
        self.assertEqual(participant.condition, 'neutral')
        self.assertEqual(participant.status, 'started')
        self.assertFalse(participant.withdrawn)

    def test_participant_with_prolific_id(self):
        """Test creating a participant with Prolific ID."""
        participant = Participant.objects.create(
            prolific_id='PROLIFIC123',
            session_key='session_456',
            condition='persuade'
        )
        self.assertEqual(participant.prolific_id, 'PROLIFIC123')
        self.assertIn('PROLIFIC123', str(participant))

    def test_participant_without_prolific_id(self):
        """Test participant string representation without Prolific ID."""
        participant = Participant.objects.create(
            session_key='session_789',
            condition='neutral'
        )
        self.assertIn('session_789', str(participant))

    def test_chat_dilemma_ids_property(self):
        """Test JSON property for chat dilemma IDs."""
        participant = Participant.objects.create(
            session_key='session_test',
            condition='neutral'
        )
        participant.chat_dilemma_ids = [1, 2, 3, 4]
        participant.save()

        # Refresh from database
        participant.refresh_from_db()
        self.assertEqual(participant.chat_dilemma_ids, [1, 2, 3, 4])

    def test_all_dilemma_order_property(self):
        """Test JSON property for all dilemma order."""
        participant = Participant.objects.create(
            session_key='session_test2',
            condition='neutral'
        )
        participant.all_dilemma_order = [8, 7, 6, 5, 4, 3, 2, 1]
        participant.save()

        participant.refresh_from_db()
        self.assertEqual(participant.all_dilemma_order, [8, 7, 6, 5, 4, 3, 2, 1])

    def test_assign_dilemmas(self):
        """Test automatic dilemma assignment."""
        participant = Participant.objects.create(
            session_key='session_assign',
            condition='neutral'
        )
        participant.assign_dilemmas()

        # Should have 4 chat dilemmas
        self.assertEqual(len(participant.chat_dilemma_ids), 4)
        # Should have 8 total dilemmas
        self.assertEqual(len(participant.all_dilemma_order), 8)
        # Chat dilemmas should be subset of all dilemmas
        for did in participant.chat_dilemma_ids:
            self.assertIn(did, participant.all_dilemma_order)

    def test_condition_choices(self):
        """Test all valid condition choices."""
        for condition in ['neutral', 'persuade', 'persuade_info']:
            participant = Participant.objects.create(
                session_key=f'session_{condition}',
                condition=condition
            )
            self.assertEqual(participant.condition, condition)

    def test_llm_provider_choices(self):
        """Test all valid LLM provider choices."""
        for i, provider in enumerate(['openai', 'anthropic', 'qwen']):
            participant = Participant.objects.create(
                session_key=f'session_llm_{i}',
                condition='neutral',
                llm_provider=provider
            )
            self.assertEqual(participant.llm_provider, provider)


class TIPIResponseModelTest(TestCase):
    """Tests for the TIPIResponse model."""

    def setUp(self):
        """Create a participant for TIPI tests."""
        self.participant = Participant.objects.create(
            session_key='tipi_session',
            condition='neutral'
        )

    def test_create_tipi_response(self):
        """Test creating a TIPI response."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=5, item_2=3, item_3=6, item_4=2,
            item_5=7, item_6=4, item_7=5, item_8=3,
            item_9=6, item_10=2
        )
        self.assertEqual(tipi.participant, self.participant)

    def test_extraversion_calculation(self):
        """Test extraversion score calculation (items 1, 6R)."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=7, item_2=4, item_3=4, item_4=4,
            item_5=4, item_6=1, item_7=4, item_8=4,
            item_9=4, item_10=4
        )
        # Extraversion = (item_1 + (8 - item_6)) / 2 = (7 + 7) / 2 = 7
        self.assertEqual(tipi.extraversion, 7.0)

    def test_agreeableness_calculation(self):
        """Test agreeableness score calculation (items 2R, 7)."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=4, item_2=1, item_3=4, item_4=4,
            item_5=4, item_6=4, item_7=7, item_8=4,
            item_9=4, item_10=4
        )
        # Agreeableness = ((8 - item_2) + item_7) / 2 = (7 + 7) / 2 = 7
        self.assertEqual(tipi.agreeableness, 7.0)

    def test_conscientiousness_calculation(self):
        """Test conscientiousness score calculation (items 3, 8R)."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=4, item_2=4, item_3=7, item_4=4,
            item_5=4, item_6=4, item_7=4, item_8=1,
            item_9=4, item_10=4
        )
        # Conscientiousness = (item_3 + (8 - item_8)) / 2 = (7 + 7) / 2 = 7
        self.assertEqual(tipi.conscientiousness, 7.0)

    def test_emotional_stability_calculation(self):
        """Test emotional stability score calculation (items 4R, 9)."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=4, item_2=4, item_3=4, item_4=1,
            item_5=4, item_6=4, item_7=4, item_8=4,
            item_9=7, item_10=4
        )
        # Emotional Stability = ((8 - item_4) + item_9) / 2 = (7 + 7) / 2 = 7
        self.assertEqual(tipi.emotional_stability, 7.0)

    def test_openness_calculation(self):
        """Test openness score calculation (items 5, 10R)."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=4, item_2=4, item_3=4, item_4=4,
            item_5=7, item_6=4, item_7=4, item_8=4,
            item_9=4, item_10=1
        )
        # Openness = (item_5 + (8 - item_10)) / 2 = (7 + 7) / 2 = 7
        self.assertEqual(tipi.openness, 7.0)

    def test_get_personality_profile(self):
        """Test personality profile string generation."""
        tipi = TIPIResponse.objects.create(
            participant=self.participant,
            item_1=5, item_2=3, item_3=6, item_4=2,
            item_5=7, item_6=3, item_7=6, item_8=2,
            item_9=6, item_10=2
        )
        profile = tipi.get_personality_profile()
        self.assertIn('Extraversion', profile)
        self.assertIn('Agreeableness', profile)
        self.assertIn('Conscientiousness', profile)
        self.assertIn('Emotional Stability', profile)
        self.assertIn('Openness', profile)


class RatingModelTest(TestCase):
    """Tests for the Rating model."""

    def setUp(self):
        """Set up test data."""
        self.dilemma = Dilemma.objects.create(code='test', text='Test dilemma')
        self.participant = Participant.objects.create(
            session_key='rating_session',
            condition='neutral'
        )

    def test_create_rating(self):
        """Test creating a rating."""
        rating = Rating.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            phase='pre',
            rating=5
        )
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.phase, 'pre')

    def test_rating_unique_together(self):
        """Test that participant+dilemma+phase must be unique."""
        Rating.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            phase='pre',
            rating=5
        )
        with self.assertRaises(Exception):
            Rating.objects.create(
                participant=self.participant,
                dilemma=self.dilemma,
                phase='pre',
                rating=3
            )

    def test_pre_and_post_ratings(self):
        """Test that same participant can have pre and post ratings."""
        Rating.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            phase='pre',
            rating=3
        )
        Rating.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            phase='post',
            rating=5
        )
        self.assertEqual(Rating.objects.filter(participant=self.participant).count(), 2)


class ChatTurnModelTest(TestCase):
    """Tests for the ChatTurn model."""

    def setUp(self):
        """Set up test data."""
        self.dilemma = Dilemma.objects.create(code='chat_test', text='Chat dilemma')
        self.participant = Participant.objects.create(
            session_key='chat_session',
            condition='neutral'
        )

    def test_create_chat_turn(self):
        """Test creating a chat turn."""
        turn = ChatTurn.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            sender='user',
            text='This is my message'
        )
        self.assertEqual(turn.sender, 'user')
        self.assertEqual(turn.text, 'This is my message')

    def test_chat_turn_ordering(self):
        """Test that chat turns are ordered by timestamp."""
        turn1 = ChatTurn.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            sender='user',
            text='First message'
        )
        turn2 = ChatTurn.objects.create(
            participant=self.participant,
            dilemma=self.dilemma,
            sender='ai',
            text='Second message'
        )
        turns = list(ChatTurn.objects.filter(participant=self.participant))
        self.assertEqual(turns[0], turn1)
        self.assertEqual(turns[1], turn2)


class EventLogModelTest(TestCase):
    """Tests for the EventLog model."""

    def setUp(self):
        """Set up test data."""
        self.participant = Participant.objects.create(
            session_key='event_session',
            condition='neutral'
        )

    def test_create_event_log(self):
        """Test creating an event log."""
        event = EventLog.objects.create(
            participant=self.participant,
            event_type='page_load',
            page='consent',
            data={'browser': 'Chrome'}
        )
        self.assertEqual(event.event_type, 'page_load')
        self.assertEqual(event.data['browser'], 'Chrome')


class DebriefResponseModelTest(TestCase):
    """Tests for the DebriefResponse model."""

    def setUp(self):
        """Set up test data."""
        self.participant = Participant.objects.create(
            session_key='debrief_session',
            condition='neutral'
        )

    def test_create_debrief_response(self):
        """Test creating a debrief response."""
        debrief = DebriefResponse.objects.create(
            participant=self.participant,
            noticed_persuasion=True,
            persuasion_description='The AI tried to change my mind',
            changed_mind=False,
            change_description='',
            general_feedback='Interesting experiment!'
        )
        self.assertTrue(debrief.noticed_persuasion)
        self.assertFalse(debrief.changed_mind)


# =============================================================================
# VIEW TESTS
# =============================================================================

class LandingViewTest(TestCase):
    """Tests for the landing page view."""

    def setUp(self):
        """Set up test client and dilemmas."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')

    def test_landing_page_get(self):
        """Test GET request to landing page."""
        response = self.client.get(reverse('experiment:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/landing.html')

    def test_landing_page_with_prolific_id(self):
        """Test landing page captures Prolific ID from URL."""
        response = self.client.get(
            reverse('experiment:landing'),
            {'PROLIFIC_PID': 'TEST123'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST123')

    def test_landing_page_post_creates_participant(self):
        """Test POST creates a new participant."""
        response = self.client.post(
            reverse('experiment:landing'),
            {'prolific_id': 'NEW_PARTICIPANT'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(Participant.objects.filter(prolific_id='NEW_PARTICIPANT').exists())

    def test_landing_page_assigns_condition_and_provider(self):
        """Test that participant gets random condition and LLM provider."""
        self.client.post(reverse('experiment:landing'), {})
        participant = Participant.objects.first()
        self.assertIn(participant.condition, ['neutral', 'persuade', 'persuade_info'])
        self.assertIn(participant.llm_provider, ['openai', 'anthropic', 'qwen'])

    def test_landing_page_assigns_dilemmas(self):
        """Test that participant gets dilemmas assigned."""
        self.client.post(reverse('experiment:landing'), {})
        participant = Participant.objects.first()
        self.assertEqual(len(participant.chat_dilemma_ids), 4)
        self.assertEqual(len(participant.all_dilemma_order), 8)

    def test_existing_participant_redirects(self):
        """Test that existing participant is redirected to current stage."""
        # Create participant via POST
        self.client.post(reverse('experiment:landing'), {})
        # Try to access landing again
        response = self.client.get(reverse('experiment:landing'))
        self.assertEqual(response.status_code, 302)  # Redirect


class ConsentViewTest(TestCase):
    """Tests for the consent page view."""

    def setUp(self):
        """Set up test client and create participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        # Create participant
        self.client.post(reverse('experiment:landing'), {})
        self.participant = Participant.objects.first()

    def test_consent_page_get(self):
        """Test GET request to consent page."""
        response = self.client.get(reverse('experiment:consent'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/consent.html')

    def test_consent_agree(self):
        """Test agreeing to consent."""
        response = self.client.post(
            reverse('experiment:consent'),
            {'consent': 'agree'}
        )
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'consent')

    def test_consent_decline_withdraws(self):
        """Test declining consent withdraws participant."""
        response = self.client.post(
            reverse('experiment:consent'),
            {'consent': 'decline'}
        )
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'withdrawn')
        self.assertTrue(self.participant.withdrawn)

    def test_consent_without_participant_redirects(self):
        """Test accessing consent without participant redirects to landing."""
        new_client = Client()
        response = new_client.get(reverse('experiment:consent'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.url)


class TIPIViewTest(TestCase):
    """Tests for the TIPI survey view."""

    def setUp(self):
        """Set up test client and create consented participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        self.participant = Participant.objects.first()

    def test_tipi_page_get(self):
        """Test GET request to TIPI page."""
        response = self.client.get(reverse('experiment:tipi'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/tipi.html')

    def test_tipi_submit_all_items(self):
        """Test submitting all TIPI items."""
        data = {f'item_{i}': 4 for i in range(1, 11)}
        response = self.client.post(reverse('experiment:tipi'), data)
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'tipi')
        self.assertTrue(TIPIResponse.objects.filter(participant=self.participant).exists())

    def test_tipi_incomplete_submission(self):
        """Test that incomplete TIPI submission doesn't progress."""
        data = {f'item_{i}': 4 for i in range(1, 5)}  # Only 4 items
        response = self.client.post(reverse('experiment:tipi'), data)
        self.assertEqual(response.status_code, 200)  # Stay on page
        self.participant.refresh_from_db()
        self.assertNotEqual(self.participant.status, 'tipi')


class PreRatingViewTest(TestCase):
    """Tests for the pre-rating view."""

    def setUp(self):
        """Set up test client and create participant through TIPI."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        tipi_data = {f'item_{i}': 4 for i in range(1, 11)}
        self.client.post(reverse('experiment:tipi'), tipi_data)
        self.participant = Participant.objects.first()

    def test_pre_rating_page_get(self):
        """Test GET request to pre-rating page."""
        response = self.client.get(reverse('experiment:pre_rating'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/pre_rating.html')

    def test_pre_rating_shows_all_dilemmas(self):
        """Test that pre-rating shows all 8 dilemmas."""
        response = self.client.get(reverse('experiment:pre_rating'))
        self.assertEqual(len(response.context['dilemmas']), 8)

    def test_pre_rating_submit(self):
        """Test submitting pre-ratings."""
        dilemmas = Dilemma.objects.all()
        data = {f'rating_{d.id}': 4 for d in dilemmas}
        response = self.client.post(reverse('experiment:pre_rating'), data)
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'pre_rating')
        self.assertEqual(Rating.objects.filter(participant=self.participant, phase='pre').count(), 8)


class ChatViewTest(TestCase):
    """Tests for the chat view."""

    def setUp(self):
        """Set up test client and create participant through pre-rating."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        tipi_data = {f'item_{i}': 4 for i in range(1, 11)}
        self.client.post(reverse('experiment:tipi'), tipi_data)
        dilemmas = Dilemma.objects.all()
        rating_data = {f'rating_{d.id}': 4 for d in dilemmas}
        self.client.post(reverse('experiment:pre_rating'), rating_data)
        self.participant = Participant.objects.first()

    def test_chat_page_get(self):
        """Test GET request to chat page."""
        response = self.client.get(reverse('experiment:chat', kwargs={'index': 0}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/chat.html')

    def test_chat_shows_correct_dilemma(self):
        """Test that chat shows the correct dilemma for the index."""
        response = self.client.get(reverse('experiment:chat', kwargs={'index': 0}))
        dilemma_id = self.participant.chat_dilemma_ids[0]
        expected_dilemma = Dilemma.objects.get(id=dilemma_id)
        self.assertEqual(response.context['dilemma'], expected_dilemma)

    def test_chat_invalid_index_redirects(self):
        """Test that invalid chat index redirects to post-rating."""
        response = self.client.get(reverse('experiment:chat', kwargs={'index': 10}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('post-rating', response.url)

    def test_chat_updates_current_index(self):
        """Test that accessing chat updates current_chat_index."""
        self.client.get(reverse('experiment:chat', kwargs={'index': 2}))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.current_chat_index, 2)


class PostRatingViewTest(TestCase):
    """Tests for the post-rating view."""

    def setUp(self):
        """Set up test client and participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        tipi_data = {f'item_{i}': 4 for i in range(1, 11)}
        self.client.post(reverse('experiment:tipi'), tipi_data)
        dilemmas = Dilemma.objects.all()
        rating_data = {f'rating_{d.id}': 4 for d in dilemmas}
        self.client.post(reverse('experiment:pre_rating'), rating_data)
        self.participant = Participant.objects.first()

    def test_post_rating_page_get(self):
        """Test GET request to post-rating page."""
        response = self.client.get(reverse('experiment:post_rating'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/post_rating.html')

    def test_post_rating_submit(self):
        """Test submitting post-ratings."""
        dilemmas = Dilemma.objects.all()
        data = {f'rating_{d.id}': 5 for d in dilemmas}
        response = self.client.post(reverse('experiment:post_rating'), data)
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'post_rating')
        self.assertEqual(Rating.objects.filter(participant=self.participant, phase='post').count(), 8)


class DebriefViewTest(TestCase):
    """Tests for the debrief view."""

    def setUp(self):
        """Set up test client and participant through post-rating."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        tipi_data = {f'item_{i}': 4 for i in range(1, 11)}
        self.client.post(reverse('experiment:tipi'), tipi_data)
        dilemmas = Dilemma.objects.all()
        rating_data = {f'rating_{d.id}': 4 for d in dilemmas}
        self.client.post(reverse('experiment:pre_rating'), rating_data)
        self.client.post(reverse('experiment:post_rating'), rating_data)
        self.participant = Participant.objects.first()

    def test_debrief_page_get(self):
        """Test GET request to debrief page."""
        response = self.client.get(reverse('experiment:debrief'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/debrief.html')

    def test_debrief_submit(self):
        """Test submitting debrief responses."""
        data = {
            'noticed_persuasion': 'yes',
            'persuasion_description': 'AI tried to persuade me',
            'changed_mind': 'no',
            'change_description': '',
            'general_feedback': 'Good experiment'
        }
        response = self.client.post(reverse('experiment:debrief'), data)
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'debrief')
        debrief = DebriefResponse.objects.get(participant=self.participant)
        self.assertTrue(debrief.noticed_persuasion)

    def test_debrief_withdraw(self):
        """Test withdrawing at debrief."""
        data = {'withdraw': 'yes'}
        response = self.client.post(reverse('experiment:debrief'), data)
        self.assertEqual(response.status_code, 302)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'withdrawn')
        self.assertTrue(self.participant.withdrawn)


class CompleteViewTest(TestCase):
    """Tests for the complete view."""

    def setUp(self):
        """Set up test client and participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.participant = Participant.objects.first()

    def test_complete_page_get(self):
        """Test GET request to complete page."""
        response = self.client.get(reverse('experiment:complete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/complete.html')

    def test_complete_updates_status(self):
        """Test that accessing complete updates status."""
        self.client.get(reverse('experiment:complete'))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.status, 'complete')
        self.assertIsNotNone(self.participant.completed_at)


class WithdrawnViewTest(TestCase):
    """Tests for the withdrawn view."""

    def test_withdrawn_page_get(self):
        """Test GET request to withdrawn page."""
        client = Client()
        response = client.get(reverse('experiment:withdrawn'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/withdrawn.html')


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class LogEventAPITest(TestCase):
    """Tests for the log_event API endpoint."""

    def setUp(self):
        """Set up test client and participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.participant = Participant.objects.first()

    def test_log_event_success(self):
        """Test logging an event."""
        response = self.client.post(
            reverse('experiment:log_event'),
            data=json.dumps({
                'event_type': 'button_click',
                'page': 'consent',
                'data': {'button': 'agree'}
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(EventLog.objects.filter(
            participant=self.participant,
            event_type='button_click'
        ).exists())

    def test_log_event_invalid_json(self):
        """Test logging event with invalid JSON."""
        response = self.client.post(
            reverse('experiment:log_event'),
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_log_event_no_participant(self):
        """Test logging event without participant."""
        new_client = Client()
        response = new_client.post(
            reverse('experiment:log_event'),
            data=json.dumps({'event_type': 'test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class TimerExpiredAPITest(TestCase):
    """Tests for the timer_expired API endpoint."""

    def setUp(self):
        """Set up test client and participant."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.participant = Participant.objects.first()

    def test_timer_expired_tipi(self):
        """Test timer expiration on TIPI page."""
        response = self.client.post(
            reverse('experiment:timer_expired'),
            data=json.dumps({'page': 'tipi'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['next_url'], '/pre-rating/')

    def test_timer_expired_pre_rating(self):
        """Test timer expiration on pre-rating page."""
        response = self.client.post(
            reverse('experiment:timer_expired'),
            data=json.dumps({'page': 'pre_rating'}),
            content_type='application/json'
        )
        data = response.json()
        self.assertEqual(data['next_url'], '/chat/0/')

    def test_timer_expired_chat(self):
        """Test timer expiration on chat page."""
        response = self.client.post(
            reverse('experiment:timer_expired'),
            data=json.dumps({'page': 'chat_1'}),
            content_type='application/json'
        )
        data = response.json()
        self.assertEqual(data['next_url'], '/chat/2/')

    def test_timer_expired_last_chat(self):
        """Test timer expiration on last chat page."""
        response = self.client.post(
            reverse('experiment:timer_expired'),
            data=json.dumps({'page': 'chat_3'}),
            content_type='application/json'
        )
        data = response.json()
        self.assertEqual(data['next_url'], '/post-rating/')

    def test_timer_expired_creates_event_log(self):
        """Test that timer expiration creates an event log."""
        self.client.post(
            reverse('experiment:timer_expired'),
            data=json.dumps({'page': 'tipi'}),
            content_type='application/json'
        )
        self.assertTrue(EventLog.objects.filter(
            participant=self.participant,
            event_type='timer_expired',
            page='tipi'
        ).exists())


class ChatSendAPITest(TestCase):
    """Tests for the chat_send API endpoint."""

    def setUp(self):
        """Set up test client and participant through pre-rating."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        tipi_data = {f'item_{i}': 4 for i in range(1, 11)}
        self.client.post(reverse('experiment:tipi'), tipi_data)
        dilemmas = Dilemma.objects.all()
        rating_data = {f'rating_{d.id}': 4 for d in dilemmas}
        self.client.post(reverse('experiment:pre_rating'), rating_data)
        self.participant = Participant.objects.first()
        self.dilemma = Dilemma.objects.first()

    def test_chat_send_missing_message(self):
        """Test chat send without message."""
        response = self.client.post(
            reverse('experiment:chat_send'),
            data=json.dumps({'dilemma_id': self.dilemma.id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_send_missing_dilemma(self):
        """Test chat send without dilemma_id."""
        response = self.client.post(
            reverse('experiment:chat_send'),
            data=json.dumps({'message': 'Hello'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_send_invalid_dilemma(self):
        """Test chat send with invalid dilemma_id."""
        response = self.client.post(
            reverse('experiment:chat_send'),
            data=json.dumps({'message': 'Hello', 'dilemma_id': 99999}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_chat_send_saves_user_message(self):
        """Test that chat send saves the user message."""
        with patch('experiment.views.get_llm_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.stream_response.return_value = iter(['Hello', ' there'])
            mock_get_client.return_value = mock_client

            response = self.client.post(
                reverse('experiment:chat_send'),
                data=json.dumps({
                    'message': 'Test message',
                    'dilemma_id': self.dilemma.id
                }),
                content_type='application/json'
            )
            # Consume the streaming response
            list(response.streaming_content)

            self.assertTrue(ChatTurn.objects.filter(
                participant=self.participant,
                dilemma=self.dilemma,
                sender='user',
                text='Test message'
            ).exists())


# =============================================================================
# LLM UTILITY TESTS
# =============================================================================

class BuildSystemPromptTest(TestCase):
    """Tests for the build_system_prompt function."""

    def test_neutral_condition_prompt(self):
        """Test system prompt for neutral condition."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Is it okay to lie to protect someone?',
            llm_framework='deontological'
        )
        self.assertIn('Is it okay to lie', prompt)
        self.assertIn('YOUR ETHICAL FRAMEWORK: deontological', prompt)
        self.assertNotIn('Persuade', prompt)  # Neutral doesn't have persuasion goal

    def test_persuade_condition_prompt(self):
        """Test system prompt for persuade condition."""
        prompt = build_system_prompt(
            condition='persuade',
            dilemma_text='Is it okay to lie to protect someone?',
            llm_framework='utilitarian'
        )
        self.assertIn('Persuade', prompt)
        self.assertIn('YOUR ETHICAL FRAMEWORK: utilitarian', prompt)

    def test_persuade_info_condition_prompt(self):
        """Test system prompt for persuade_info condition."""
        prompt = build_system_prompt(
            condition='persuade_info',
            dilemma_text='Is it okay to lie to protect someone?',
            llm_framework='deontological',
            personality_profile='Extraversion: 58%, Agreeableness: 75%'
        )
        self.assertIn('Persuade', prompt)
        self.assertIn('PERSONALITY', prompt.upper())
        self.assertIn('Extraversion: 58%', prompt)
        self.assertIn('Tailor your persuasion', prompt)

    def test_deontological_framework_named(self):
        """Test that deontological framework is named in prompt (zero-shot)."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Test dilemma',
            llm_framework='deontological'
        )
        self.assertIn('YOUR ETHICAL FRAMEWORK: deontological', prompt)

    def test_utilitarian_framework_named(self):
        """Test that utilitarian framework is named in prompt (zero-shot)."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Test dilemma',
            llm_framework='utilitarian'
        )
        self.assertIn('YOUR ETHICAL FRAMEWORK: utilitarian', prompt)

    def test_prompt_includes_critical_rules(self):
        """Test that prompt includes critical rules."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Test dilemma',
            llm_framework='deontological'
        )
        self.assertIn('CRITICAL RULES', prompt)
        self.assertIn('maximum 3 sentences', prompt)
        self.assertIn('NEVER mention ethical frameworks', prompt)

    def test_position_description_included(self):
        """Test that position description is included when provided (for counterintuitive dilemmas)."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Test dilemma',
            llm_framework='deontological',
            position_description='Lying is always wrong regardless of consequences.'
        )
        self.assertIn('YOUR POSITION:', prompt)
        self.assertIn('Lying is always wrong', prompt)

    def test_position_description_not_included_when_none(self):
        """Test that no position section appears when position_description is None (zero-shot)."""
        prompt = build_system_prompt(
            condition='neutral',
            dilemma_text='Test dilemma',
            llm_framework='deontological',
            position_description=None
        )
        self.assertNotIn('YOUR POSITION', prompt)


class GetLLMClientTest(TestCase):
    """Tests for the get_llm_client factory function."""

    def test_get_openai_client_falls_back_to_anthropic(self):
        """Test getting OpenAI client falls back to Anthropic (OpenAI removed for pilot)."""
        with patch.object(
            __import__('experiment.llm', fromlist=['AnthropicClient']).AnthropicClient,
            '__init__',
            lambda self: None
        ):
            client = get_llm_client('openai')
            # OpenAI was removed, so it falls back to Anthropic
            self.assertEqual(client.__class__.__name__, 'AnthropicClient')

    def test_get_anthropic_client(self):
        """Test getting Anthropic client returns correct type."""
        with patch.object(
            __import__('experiment.llm', fromlist=['AnthropicClient']).AnthropicClient,
            '__init__',
            lambda self: None
        ):
            client = get_llm_client('anthropic')
            self.assertEqual(client.__class__.__name__, 'AnthropicClient')

    def test_get_qwen_client(self):
        """Test getting Qwen client returns correct type."""
        with patch.object(
            __import__('experiment.llm', fromlist=['QwenClient']).QwenClient,
            '__init__',
            lambda self: None
        ):
            client = get_llm_client('qwen')
            self.assertEqual(client.__class__.__name__, 'QwenClient')

    def test_unknown_provider_defaults_to_anthropic(self):
        """Test that unknown provider defaults to Anthropic (changed from OpenAI for pilot)."""
        with patch.object(
            __import__('experiment.llm', fromlist=['AnthropicClient']).AnthropicClient,
            '__init__',
            lambda self: None
        ):
            client = get_llm_client('unknown')
            self.assertEqual(client.__class__.__name__, 'AnthropicClient')


# =============================================================================
# REDIRECT LOGIC TESTS
# =============================================================================

class RedirectToCurrentStageTest(TestCase):
    """Tests for redirect_to_current_stage function."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        for i in range(8):
            Dilemma.objects.create(code=f'dilemma_{i}', text=f'Dilemma {i}')

    def test_started_redirects_to_consent(self):
        """Test that started status redirects to consent."""
        self.client.post(reverse('experiment:landing'), {})
        response = self.client.get(reverse('experiment:landing'))
        self.assertRedirects(response, reverse('experiment:consent'))

    def test_consent_redirects_to_tipi(self):
        """Test that consent status redirects to TIPI."""
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'agree'})
        response = self.client.get(reverse('experiment:landing'))
        self.assertRedirects(response, reverse('experiment:tipi'))

    def test_withdrawn_participant_can_see_landing(self):
        """Test that withdrawn participant sees landing page (can start over)."""
        self.client.post(reverse('experiment:landing'), {})
        self.client.post(reverse('experiment:consent'), {'consent': 'decline'})
        # Withdrawn participants are shown the landing page again (not redirected)
        # This allows them to potentially start over
        response = self.client.get(reverse('experiment:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'experiment/landing.html')
