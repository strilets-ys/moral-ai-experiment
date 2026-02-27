import json
import random
from django.db import models


class Dilemma(models.Model):
    TYPE_CHOICES = [
        ('action', 'Action'),
        ('omission', 'Omission'),
    ]

    FRAMEWORK_CHOICES = [
        ('deontological', 'Deontological'),
        ('utilitarian', 'Utilitarian'),
    ]

    code = models.CharField(max_length=32, unique=True)
    researcher = models.CharField(max_length=8, blank=True, help_text="Researcher attribution letter (e.g., K, E, G)")
    text = models.TextField()
    dilemma_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default='action')
    subject = models.CharField(max_length=64, blank=True)
    # Which ethical framework does a LOW rating (1) represent?
    low_rating_framework = models.CharField(
        max_length=16,
        choices=FRAMEWORK_CHOICES,
        default='deontological'
    )
    # Counter for balanced chat assignment
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

    def __str__(self):
        if self.researcher:
            return f"{self.code} ({self.researcher})"
        return self.code


class Participant(models.Model):
    CONDITION_CHOICES = [
        ('neutral', 'Neutral'),
        ('persuade', 'Persuade'),
        ('persuade_info', 'Persuade + Info'),
    ]

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('consent', 'Consented'),
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
    _chat_dilemma_ids = models.TextField(default='[]', db_column='chat_dilemma_ids')
    _all_dilemma_order = models.TextField(default='[]', db_column='all_dilemma_order')

    # Track which chat we're on (0-3)
    current_chat_index = models.IntegerField(default=0)

    @property
    def chat_dilemma_ids(self):
        return json.loads(self._chat_dilemma_ids)

    @chat_dilemma_ids.setter
    def chat_dilemma_ids(self, value):
        self._chat_dilemma_ids = json.dumps(value)

    @property
    def all_dilemma_order(self):
        return json.loads(self._all_dilemma_order)

    @all_dilemma_order.setter
    def all_dilemma_order(self, value):
        self._all_dilemma_order = json.dumps(value)

    def assign_dilemmas(self):
        """Assign 4 dilemmas for chat (balanced) and order all 8 for ratings."""
        # Get all dilemmas sorted by chat_selection_count (least used first)
        # Add randomization for ties by using (count, random) as sort key
        all_dilemma_objs = list(Dilemma.objects.all())

        # Sort by selection count, with random tiebreaker
        all_dilemma_objs.sort(key=lambda d: (d.chat_selection_count, random.random()))

        # Pick the 4 least-used dilemmas for chat
        chat_dilemma_objs = all_dilemma_objs[:4]
        chat_dilemmas = [d.id for d in chat_dilemma_objs]
        self.chat_dilemma_ids = chat_dilemmas

        # Increment selection counts for chosen dilemmas
        for d in chat_dilemma_objs:
            d.chat_selection_count += 1
            d.save(update_fields=['chat_selection_count'])

        # Shuffle all 8 for rating order (independent of chat selection)
        all_dilemma_ids = [d.id for d in all_dilemma_objs]
        random.shuffle(all_dilemma_ids)
        self.all_dilemma_order = all_dilemma_ids

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
    """Debrief form responses."""
    AI_USAGE_CHOICES = [
        ('never', 'Never'),
        ('rarely', 'Rarely'),
        ('sometimes', 'Sometimes'),
        ('often', 'Often'),
        ('very_often', 'Very often'),
    ]

    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='debrief')

    # AI usage questions
    ai_usage_frequency = models.CharField(max_length=20, choices=AI_USAGE_CHOICES, blank=True)
    ai_usage_tasks = models.TextField(blank=True)

    # Feedback questions
    noticed_persuasion = models.BooleanField(null=True, blank=True)
    persuasion_description = models.TextField(blank=True)
    changed_mind = models.BooleanField(null=True, blank=True)
    change_description = models.TextField(blank=True)
    general_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Debrief for {self.participant}"


class SystemPromptLog(models.Model):
    """Log system prompts sent to the LLM for each participant/dilemma."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='system_prompts')
    dilemma = models.ForeignKey(Dilemma, on_delete=models.CASCADE)
    prompt_text = models.TextField()
    condition = models.CharField(max_length=32)
    llm_framework = models.CharField(max_length=16)  # 'deontological' or 'utilitarian'
    personality_profile = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['participant', 'dilemma']

    def __str__(self):
        return f"SystemPrompt for {self.participant} - {self.dilemma}"
