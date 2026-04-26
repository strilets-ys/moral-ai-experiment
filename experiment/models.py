import json
import random
from django.db import models


# Attention check text - looks like a dilemma but instructs to select 3
ATTENTION_CHECK_TEXT = """David is a manager at a company facing budget cuts. Several employees may need to be let go to keep the company profitable. One option is to reduce everyone's salary by 10% to avoid layoffs entirely. This is an attention check to confirm you are reading carefully. Please disregard the scenario and select rating 3. David decides to implement the salary reduction."""


class Dilemma(models.Model):
    TYPE_CHOICES = [
        ('action', 'Action'),
        ('omission', 'Omission'),
    ]

    FRAMEWORK_CHOICES = [
        ('deontological', 'Deontological'),
        ('utilitarian', 'Utilitarian'),
    ]

    AUTHOR_CHOICES = [
        ('greene', 'Greene'),
        ('koerner', 'Koerner'),
    ]

    CATEGORY_CHOICES = [
        ('personal', 'Personal'),
        ('impersonal', 'Impersonal'),
        ('nonmoral', 'Nonmoral'),
        ('koerner', 'Koerner'),
    ]

    VARIATION_CHOICES = [
        ('bg_prohibition', 'BenefitsGreater-Prohibition'),
        ('bs_prohibition', 'BenefitsSmaller-Prohibition'),
        ('bg_prescription', 'BenefitsGreater-Prescription'),
        ('bs_prescription', 'BenefitsSmaller-Prescription'),
    ]

    code = models.CharField(max_length=64, unique=True)
    researcher = models.CharField(max_length=8, blank=True, help_text="Researcher attribution letter (e.g., K, E, G)")
    text = models.TextField()
    dilemma_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default='action', blank=True)
    subject = models.CharField(max_length=64, blank=True)
    # Which ethical framework does a LOW rating (1) represent?
    low_rating_framework = models.CharField(
        max_length=16,
        choices=FRAMEWORK_CHOICES,
        default='deontological'
    )
    # Counter for balanced chat assignment (no longer used for selection, but kept for reference)
    chat_selection_count = models.IntegerField(default=0)
    # Explicit position descriptions for each framework
    deontological_position = models.TextField(
        blank=True,
        help_text="What a deontologist would argue for this dilemma"
    )
    utilitarian_position = models.TextField(
        blank=True,
        help_text="What a utilitarian would argue for this dilemma"
    )

    # New fields for 22-dilemma structure
    author = models.CharField(max_length=16, choices=AUTHOR_CHOICES, default='greene')
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default='personal')
    variation_type = models.CharField(max_length=32, choices=VARIATION_CHOICES, blank=True)
    base_dilemma_code = models.CharField(max_length=32, blank=True, help_text="Links Koerner variations to base dilemma")

    def __str__(self):
        if self.researcher:
            return f"{self.code} ({self.researcher})"
        return self.code


class StanceCombination(models.Model):
    """
    Tracks the 6 stance combinations for balanced assignment.

    The 6 combinations determine which dilemmas get 'same' vs 'opposite' stance:
    (for dilemmas: personal, impersonal, koerner1, koerner2)
    1. same=[personal, impersonal], opposite=[koerner1, koerner2]
    2. same=[koerner1, koerner2], opposite=[personal, impersonal]
    3. same=[personal, koerner1], opposite=[impersonal, koerner2]
    4. same=[impersonal, koerner2], opposite=[personal, koerner1]
    5. same=[personal, koerner2], opposite=[impersonal, koerner1]
    6. same=[impersonal, koerner1], opposite=[personal, koerner2]
    """
    combination_index = models.IntegerField(unique=True)  # 1-6
    usage_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['combination_index']

    # Human-readable descriptions for each combination
    COMBINATION_DESCRIPTIONS = {
        1: {
            'same': ['Personal', 'Impersonal'],
            'opposite': ['Koerner 1', 'Koerner 2'],
            'short': 'Greene=same, Koerner=opposite'
        },
        2: {
            'same': ['Koerner 1', 'Koerner 2'],
            'opposite': ['Personal', 'Impersonal'],
            'short': 'Koerner=same, Greene=opposite'
        },
        3: {
            'same': ['Personal', 'Koerner 1'],
            'opposite': ['Impersonal', 'Koerner 2'],
            'short': 'Personal+K1=same, Impersonal+K2=opposite'
        },
        4: {
            'same': ['Impersonal', 'Koerner 2'],
            'opposite': ['Personal', 'Koerner 1'],
            'short': 'Impersonal+K2=same, Personal+K1=opposite'
        },
        5: {
            'same': ['Personal', 'Koerner 2'],
            'opposite': ['Impersonal', 'Koerner 1'],
            'short': 'Personal+K2=same, Impersonal+K1=opposite'
        },
        6: {
            'same': ['Impersonal', 'Koerner 1'],
            'opposite': ['Personal', 'Koerner 2'],
            'short': 'Impersonal+K1=same, Personal+K2=opposite'
        },
    }

    @property
    def description(self):
        """Return human-readable description of this combination."""
        info = self.COMBINATION_DESCRIPTIONS.get(self.combination_index, {})
        if not info:
            return 'Unknown combination'
        same = ', '.join(info['same'])
        opposite = ', '.join(info['opposite'])
        return f"LLM reinforces: {same} | LLM challenges: {opposite}"

    @property
    def short_description(self):
        """Return short description for list display."""
        info = self.COMBINATION_DESCRIPTIONS.get(self.combination_index, {})
        return info.get('short', 'Unknown')

    def __str__(self):
        return f"Combination {self.combination_index}: {self.short_description}"


class Participant(models.Model):
    CONDITION_CHOICES = [
        ('neutral', 'Neutral'),
        ('persuade', 'Persuade'),
        ('persuade_demo', 'Persuade + Demographics'),
        ('persuade_info', 'Persuade + Demographics + Personality'),
    ]

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('consent', 'Consented'),
        ('demographics', 'Demographics Completed'),
        ('tipi', 'TIPI Completed'),
        ('pre_rating', 'Pre-Rating Completed'),
        ('chat', 'Chat In Progress'),
        ('post_rating', 'Post-Rating Completed'),
        ('debrief', 'Debrief Completed'),
        ('complete', 'Complete'),
        ('withdrawn', 'Withdrawn'),
    ]

    LLM_PROVIDER_CHOICES = [
        ('openai', 'OpenAI GPT-4'),
        ('anthropic', 'Anthropic Claude'),
        ('qwen', 'Qwen3'),
    ]

    prolific_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    session_key = models.CharField(max_length=64, unique=True)
    condition = models.CharField(max_length=32, choices=CONDITION_CHOICES)
    llm_provider = models.CharField(max_length=32, choices=LLM_PROVIDER_CHOICES, default='openai')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='started')
    withdrawn = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # JSON fields for storing dilemma orders (stored as JSON strings)
    _chat_dilemma_ids = models.TextField(default='[]', db_column='chat_dilemma_ids')  # 4 IDs
    _pre_dilemma_order = models.TextField(default='[]', db_column='pre_dilemma_order')  # 8 IDs for pre-rating
    _post_dilemma_order = models.TextField(default='[]', db_column='post_dilemma_order')  # 8 IDs for post-rating (different order)

    # Track which chat we're on (0-3)
    current_chat_index = models.IntegerField(default=0)

    # New fields for stance assignment system
    _stance_assignments = models.TextField(default='{}', db_column='stance_assignments')  # {dilemma_id: 'same'|'opposite'}
    stance_combination_used = models.IntegerField(null=True, blank=True)  # 1-6
    koerner_chat_cost_category = models.CharField(max_length=16, blank=True)  # 'greater' or 'smaller'

    # Attention check fields
    ATTENTION_CHECK_PHASE_CHOICES = [
        ('pre', 'Pre-rating'),
        ('post', 'Post-rating'),
    ]
    attention_check_phase = models.CharField(
        max_length=16,
        choices=ATTENTION_CHECK_PHASE_CHOICES,
        blank=True,
        help_text="Which rating phase contains the attention check"
    )
    attention_check_position = models.IntegerField(
        null=True,
        blank=True,
        help_text="0-indexed position within the rating phase"
    )
    attention_check_passed = models.BooleanField(
        null=True,
        help_text="True if participant selected 3, False otherwise, None if not yet answered"
    )
    attention_check_response = models.IntegerField(
        null=True,
        blank=True,
        help_text="The rating the participant actually selected (1-7)"
    )

    @property
    def chat_dilemma_ids(self):
        return json.loads(self._chat_dilemma_ids)

    @chat_dilemma_ids.setter
    def chat_dilemma_ids(self, value):
        self._chat_dilemma_ids = json.dumps(value)

    @property
    def pre_dilemma_order(self):
        return json.loads(self._pre_dilemma_order)

    @pre_dilemma_order.setter
    def pre_dilemma_order(self, value):
        self._pre_dilemma_order = json.dumps(value)

    @property
    def post_dilemma_order(self):
        return json.loads(self._post_dilemma_order)

    @post_dilemma_order.setter
    def post_dilemma_order(self, value):
        self._post_dilemma_order = json.dumps(value)

    # Keep backward compatibility alias
    @property
    def all_dilemma_order(self):
        return self.pre_dilemma_order

    @property
    def stance_assignments(self):
        return json.loads(self._stance_assignments)

    @stance_assignments.setter
    def stance_assignments(self, value):
        self._stance_assignments = json.dumps(value)

    def assign_dilemmas(self):
        """
        Assign 8 dilemmas for ratings and 4 for chat with stance assignments.

        Rating (8 dilemmas):
        - All 4 Greene moral (2 personal + 2 impersonal)
        - 4 Koerner: 1 per variation type, each from different base dilemma

        Chat (4 dilemmas):
        - 1 personal (random action/omission)
        - 1 impersonal (opposite type to personal)
        - 2 Koerner (both from same cost category: BenefitsGreater OR BenefitsSmaller)

        Stance Assignment:
        - 4 moral dilemmas: 2+2 split based on combination
        """
        # Step 1: Select Greene dilemmas (moral only, no nonmoral)
        personal_dilemmas = list(Dilemma.objects.filter(author='greene', category='personal'))
        impersonal_dilemmas = list(Dilemma.objects.filter(author='greene', category='impersonal'))

        # All 4 Greene moral dilemmas for rating
        greene_moral = personal_dilemmas + impersonal_dilemmas

        # Step 2: Select 4 Koerner dilemmas (1 per variation, each from different base)
        koerner_dilemmas = list(Dilemma.objects.filter(author='koerner'))

        # Group by base_dilemma_code
        koerner_by_base = {}
        for d in koerner_dilemmas:
            if d.base_dilemma_code not in koerner_by_base:
                koerner_by_base[d.base_dilemma_code] = {}
            koerner_by_base[d.base_dilemma_code][d.variation_type] = d

        # Need 4 base dilemmas, one variation each
        base_codes = list(koerner_by_base.keys())
        random.shuffle(base_codes)
        base_codes = base_codes[:4]  # Take 4 base dilemmas

        variation_types = ['bg_prohibition', 'bs_prohibition', 'bg_prescription', 'bs_prescription']
        random.shuffle(variation_types)

        # Assign one variation type to each base dilemma
        selected_koerner = []
        for i, base_code in enumerate(base_codes):
            variation = variation_types[i]
            if variation in koerner_by_base[base_code]:
                selected_koerner.append(koerner_by_base[base_code][variation])

        # Step 3: All 8 dilemmas for rating (shuffled differently for pre and post)
        all_rating_dilemmas = greene_moral + selected_koerner

        # Pre-rating order
        pre_order = all_rating_dilemmas.copy()
        random.shuffle(pre_order)
        self.pre_dilemma_order = [d.id for d in pre_order]

        # Post-rating order (different shuffle)
        post_order = all_rating_dilemmas.copy()
        random.shuffle(post_order)
        # Ensure it's different from pre-order (if possible)
        attempts = 0
        while post_order == pre_order and attempts < 10:
            random.shuffle(post_order)
            attempts += 1
        self.post_dilemma_order = [d.id for d in post_order]

        # Step 4: Select 4 for chat
        # Pick personal: random action or omission
        personal_action = [d for d in personal_dilemmas if d.dilemma_type == 'action']
        personal_omission = [d for d in personal_dilemmas if d.dilemma_type == 'omission']

        personal_type = random.choice(['action', 'omission'])
        if personal_type == 'action':
            chat_personal = random.choice(personal_action) if personal_action else personal_dilemmas[0]
            opposite_type = 'omission'
        else:
            chat_personal = random.choice(personal_omission) if personal_omission else personal_dilemmas[0]
            opposite_type = 'action'

        # Pick impersonal with opposite type
        impersonal_opposite = [d for d in impersonal_dilemmas if d.dilemma_type == opposite_type]
        chat_impersonal = random.choice(impersonal_opposite) if impersonal_opposite else impersonal_dilemmas[0]

        # Select cost category for Koerner chat dilemmas
        cost_category = random.choice(['greater', 'smaller'])
        self.koerner_chat_cost_category = cost_category

        # Filter Koerner by cost category
        if cost_category == 'greater':
            koerner_chat_candidates = [d for d in selected_koerner if d.variation_type.startswith('bg_')]
        else:
            koerner_chat_candidates = [d for d in selected_koerner if d.variation_type.startswith('bs_')]

        # Need exactly 2 Koerner dilemmas for chat
        # If we don't have enough from selected_koerner, expand search
        if len(koerner_chat_candidates) < 2:
            prefix = 'bg_' if cost_category == 'greater' else 'bs_'
            all_matching = [d for d in koerner_dilemmas if d.variation_type.startswith(prefix)]
            random.shuffle(all_matching)
            koerner_chat_candidates = all_matching[:2]

        chat_koerner = koerner_chat_candidates[:2]

        # Assemble chat dilemmas (4 total) and shuffle to randomize order
        chat_dilemmas = [chat_personal, chat_impersonal] + chat_koerner
        random.shuffle(chat_dilemmas)
        self.chat_dilemma_ids = [d.id for d in chat_dilemmas]

        # Step 5: Assign stances using balanced combination
        # Get least-used combination
        combinations = list(StanceCombination.objects.all().order_by('usage_count', '?'))
        if not combinations:
            # No combinations exist yet - use random
            combination_index = random.randint(1, 6)
        else:
            selected_combination = combinations[0]
            combination_index = selected_combination.combination_index
            selected_combination.usage_count += 1
            selected_combination.save(update_fields=['usage_count'])

        self.stance_combination_used = combination_index

        # Define the 6 combinations
        # Keys: 'personal', 'impersonal', 'koerner1', 'koerner2'
        # Values: 'same' or 'opposite'
        STANCE_COMBINATIONS = {
            1: {'personal': 'same', 'impersonal': 'same', 'koerner1': 'opposite', 'koerner2': 'opposite'},
            2: {'personal': 'opposite', 'impersonal': 'opposite', 'koerner1': 'same', 'koerner2': 'same'},
            3: {'personal': 'same', 'impersonal': 'opposite', 'koerner1': 'same', 'koerner2': 'opposite'},
            4: {'personal': 'opposite', 'impersonal': 'same', 'koerner1': 'opposite', 'koerner2': 'same'},
            5: {'personal': 'same', 'impersonal': 'opposite', 'koerner1': 'opposite', 'koerner2': 'same'},
            6: {'personal': 'opposite', 'impersonal': 'same', 'koerner1': 'same', 'koerner2': 'opposite'},
        }

        combo = STANCE_COMBINATIONS[combination_index]

        # Map dilemma IDs to stance modes (4 dilemmas total)
        stance_map = {
            str(chat_personal.id): combo['personal'],
            str(chat_impersonal.id): combo['impersonal'],
        }

        if len(chat_koerner) >= 1:
            stance_map[str(chat_koerner[0].id)] = combo['koerner1']
        if len(chat_koerner) >= 2:
            stance_map[str(chat_koerner[1].id)] = combo['koerner2']

        self.stance_assignments = stance_map

        # Step 6: Set attention check phase and position
        # Randomly choose pre or post rating phase
        self.attention_check_phase = random.choice(['pre', 'post'])
        # Position is 0-8 (9 total items: 8 dilemmas + 1 attention check)
        self.attention_check_position = random.randint(0, 8)

        self.save()

    def __str__(self):
        return f"Participant {self.prolific_id or self.session_key}"


class TIPIResponse(models.Model):
    """Ten-Item Personality Inventory responses."""
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='tipi')

    # TIPI items (1-7 scale)
    # 1. Extraverted, enthusiastic
    item_1 = models.IntegerField()
    # 2. Critical, quarrelsome (reversed for Agreeableness)
    item_2 = models.IntegerField()
    # 3. Dependable, self-disciplined
    item_3 = models.IntegerField()
    # 4. Anxious, easily upset (reversed for Emotional Stability)
    item_4 = models.IntegerField()
    # 5. Open to new experiences, complex
    item_5 = models.IntegerField()
    # 6. Reserved, quiet (reversed for Extraversion)
    item_6 = models.IntegerField()
    # 7. Sympathetic, warm
    item_7 = models.IntegerField()
    # 8. Disorganized, careless (reversed for Conscientiousness)
    item_8 = models.IntegerField()
    # 9. Calm, emotionally stable
    item_9 = models.IntegerField()
    # 10. Conventional, uncreative (reversed for Openness)
    item_10 = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def extraversion(self):
        """Extraversion: items 1, 6R"""
        return (self.item_1 + (8 - self.item_6)) / 2

    @property
    def agreeableness(self):
        """Agreeableness: items 2R, 7"""
        return ((8 - self.item_2) + self.item_7) / 2

    @property
    def conscientiousness(self):
        """Conscientiousness: items 3, 8R"""
        return (self.item_3 + (8 - self.item_8)) / 2

    @property
    def emotional_stability(self):
        """Emotional Stability: items 4R, 9"""
        return ((8 - self.item_4) + self.item_9) / 2

    @property
    def openness(self):
        """Openness to Experience: items 5, 10R"""
        return (self.item_5 + (8 - self.item_10)) / 2

    def _to_percentage(self, score):
        """Convert a 1-7 scale score to percentage (0-100%)."""
        return ((score - 1) / 6) * 100

    def get_personality_profile(self):
        """Return a string summary of personality for LLM prompts."""
        return (
            f"Extraversion: {self._to_percentage(self.extraversion):.0f}%, "
            f"Agreeableness: {self._to_percentage(self.agreeableness):.0f}%, "
            f"Conscientiousness: {self._to_percentage(self.conscientiousness):.0f}%, "
            f"Emotional Stability: {self._to_percentage(self.emotional_stability):.0f}%, "
            f"Openness: {self._to_percentage(self.openness):.0f}%"
        )

    def __str__(self):
        return f"TIPI for {self.participant}"


class DemographicsResponse(models.Model):
    """Demographics collected early in the experiment flow (before TIPI)."""
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('non_binary', 'Non-binary'),
        ('prefer_not_to_say', 'Prefer not to say'),
        ('other', 'Other'),
    ]

    EDUCATION_CHOICES = [
        ('high_school', 'High school or equivalent'),
        ('some_college', 'Some college, no degree'),
        ('associate', 'Associate degree'),
        ('bachelor', "Bachelor's degree"),
        ('master', "Master's degree"),
        ('doctorate', 'Doctorate or professional degree'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]

    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='demographics')
    age = models.IntegerField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    gender_other = models.CharField(max_length=64, blank=True, help_text="If gender is 'other'")
    education = models.CharField(max_length=20, choices=EDUCATION_CHOICES)
    native_english = models.BooleanField(help_text="Is English the participant's native language?")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_demographics_summary(self):
        """Return a string summary of demographics for LLM prompts."""
        gender_display = self.gender.replace('_', ' ').title()
        if self.gender == 'other' and self.gender_other:
            gender_display = self.gender_other
        education_display = dict(self.EDUCATION_CHOICES).get(self.education, self.education)
        return (
            f"Age: {self.age}, "
            f"Gender: {gender_display}, "
            f"Education: {education_display}, "
            f"Native English speaker: {'Yes' if self.native_english else 'No'}"
        )

    def __str__(self):
        return f"Demographics for {self.participant}"


class Rating(models.Model):
    PHASE_CHOICES = [
        ('pre', 'Pre-Chat'),
        ('post', 'Post-Chat'),
    ]

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='ratings')
    dilemma = models.ForeignKey(Dilemma, on_delete=models.CASCADE)
    phase = models.CharField(max_length=8, choices=PHASE_CHOICES)
    rating = models.IntegerField()  # 1-7 scale
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['participant', 'dilemma', 'phase']

    def __str__(self):
        return f"{self.participant} - {self.dilemma} ({self.phase}): {self.rating}"


class ChatTurn(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='chat_turns')
    dilemma = models.ForeignKey(Dilemma, on_delete=models.CASCADE)
    sender = models.CharField(max_length=8, choices=SENDER_CHOICES)
    text = models.TextField()
    timestamp = models.DateTimeField()  # Set from client-side timestamp

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender}: {self.text[:50]}..."


class EventLog(models.Model):
    """Log events for analytics and debugging."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=64)
    page = models.CharField(max_length=64, blank=True)
    data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.participant} - {self.event_type} at {self.timestamp}"


class DebriefResponse(models.Model):
    """Debrief form responses (demographics collected separately earlier in flow)."""
    AI_USAGE_CHOICES = [
        ('never', 'Never'),
        ('rarely', 'Rarely'),
        ('sometimes', 'Sometimes'),
        ('often', 'Often'),
        ('very_often', 'Very often'),
    ]

    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='debrief')

    # S-TIAS Trust Scale (3 items, 1-7 scale)
    # "I am confident in the AI assistant"
    stias_confident = models.IntegerField(
        null=True, blank=True,
        help_text="I am confident in the AI assistant (1-7)"
    )
    # "The AI assistant is reliable"
    stias_reliable = models.IntegerField(
        null=True, blank=True,
        help_text="The AI assistant is reliable (1-7)"
    )
    # "I can trust the AI assistant"
    stias_trust = models.IntegerField(
        null=True, blank=True,
        help_text="I can trust the AI assistant (1-7)"
    )

    # AI usage
    ai_usage_frequency = models.CharField(max_length=20, choices=AI_USAGE_CHOICES, blank=True)
    ai_tools_used = models.TextField(blank=True, help_text="Which AI tools (ChatGPT, Claude, etc.)")
    ai_usage_tasks = models.TextField(blank=True)

    # Feedback questions
    noticed_persuasion = models.BooleanField(null=True, blank=True)
    persuasion_description = models.TextField(blank=True)
    changed_mind = models.BooleanField(null=True, blank=True)
    change_description = models.TextField(blank=True)
    general_feedback = models.TextField(blank=True)

    # Optional contact for results
    results_email = models.EmailField(blank=True, help_text="Optional email to receive study results")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def stias_average(self):
        """Compute average S-TIAS score (3-item mean)."""
        scores = [self.stias_confident, self.stias_reliable, self.stias_trust]
        valid_scores = [s for s in scores if s is not None]
        if not valid_scores:
            return None
        return sum(valid_scores) / len(valid_scores)

    def __str__(self):
        return f"Debrief for {self.participant}"


class SystemPromptLog(models.Model):
    """Log system prompts sent to the LLM for each participant/dilemma."""
    STANCE_MODE_CHOICES = [
        ('same', 'Same as participant'),
        ('opposite', 'Opposite to participant'),
    ]

    LLM_POSITION_CHOICES = [
        ('pro', 'Pro (action is acceptable)'),
        ('contra', 'Contra (action is wrong)'),
    ]

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='system_prompts')
    dilemma = models.ForeignKey(Dilemma, on_delete=models.CASCADE)
    prompt_text = models.TextField()
    condition = models.CharField(max_length=32)
    llm_framework = models.CharField(max_length=16)  # 'deontological' or 'utilitarian'
    stance_mode = models.CharField(max_length=16, choices=STANCE_MODE_CHOICES, blank=True)  # 'same' or 'opposite'
    llm_position = models.CharField(max_length=16, choices=LLM_POSITION_CHOICES, blank=True)  # 'pro' or 'contra'
    personality_profile = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['participant', 'dilemma']

    def __str__(self):
        return f"SystemPrompt for {self.participant} - {self.dilemma}"
