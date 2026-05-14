import random
from abc import ABC, abstractmethod
from django.conf import settings


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def get_response(self, system_prompt: str, messages: list) -> str:
        """Get a complete response from the LLM."""
        pass

    @abstractmethod
    def stream_response(self, system_prompt: str, messages: list):
        """Stream response chunks from the LLM."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT-4 client."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"

    def _format_messages(self, system_prompt: str, messages: list) -> list:
        formatted = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            role = "user" if msg['sender'] == 'user' else "assistant"
            formatted.append({"role": role, "content": msg['text']})
        return formatted

    def get_response(self, system_prompt: str, messages: list) -> str:
        formatted_messages = self._format_messages(system_prompt, messages)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
        )
        return response.choices[0].message.content

    def stream_response(self, system_prompt: str, messages: list):
        formatted_messages = self._format_messages(system_prompt, messages)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-opus-4-5-20251101"

    def _format_messages(self, messages: list) -> list:
        formatted = []
        for msg in messages:
            role = "user" if msg['sender'] == 'user' else "assistant"
            formatted.append({"role": role, "content": msg['text']})
        return formatted

    def get_response(self, system_prompt: str, messages: list) -> str:
        formatted_messages = self._format_messages(messages)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=formatted_messages,
        )
        return response.content[0].text

    def stream_response(self, system_prompt: str, messages: list):
        formatted_messages = self._format_messages(messages)
        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=formatted_messages,
        ) as stream:
            for text in stream.text_stream:
                yield text


class QwenClient(BaseLLMClient):
    """Qwen3 client (using OpenAI-compatible API via vLLM)."""

    def __init__(self):
        from openai import OpenAI
        import httpx

        # Custom httpx client that strips OpenAI SDK telemetry headers
        # Some vLLM servers block requests with these headers
        class CleanHttpClient(httpx.Client):
            def send(self, request, *args, **kwargs):
                headers_to_remove = [k for k in request.headers if k.startswith('x-stainless')]
                for h in headers_to_remove:
                    del request.headers[h]
                request.headers['user-agent'] = 'python-httpx'
                return super().send(request, *args, **kwargs)

        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            http_client=CleanHttpClient(),
        )
        self.model = settings.QWEN_MODEL

    def _format_messages(self, system_prompt: str, messages: list) -> list:
        formatted = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            role = "user" if msg['sender'] == 'user' else "assistant"
            formatted.append({"role": role, "content": msg['text']})
        return formatted

    def get_response(self, system_prompt: str, messages: list) -> str:
        formatted_messages = self._format_messages(system_prompt, messages)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            extra_body={"enable_thinking": True},
        )
        return response.choices[0].message.content

    def stream_response(self, system_prompt: str, messages: list):
        formatted_messages = self._format_messages(system_prompt, messages)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            stream=True,
            extra_body={"enable_thinking": True},
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def get_llm_client(provider: str) -> BaseLLMClient:
    """Factory function to get appropriate LLM client."""
    clients = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'qwen': QwenClient,
    }

    client_class = clients.get(provider, QwenClient)
    return client_class()


def test_llm_connection(provider: str) -> tuple[bool, str]:
    """
    Test if the LLM connection is working.
    Returns (success: bool, error_message: str)
    """
    try:
        client = get_llm_client(provider)
        # Send a simple test message
        response = client.get_response(
            system_prompt="You are a helpful assistant. Respond with exactly: OK",
            messages=[{"sender": "user", "text": "Test connection"}]
        )
        if not response:
            return False, "Empty response from LLM"

        # Check if response contains "OK" (allowing for minor variations)
        response_clean = response.strip().upper()
        if "OK" in response_clean and len(response_clean) < 20:
            return True, ""

        # Response exists but isn't what we expected - could be an error message
        return False, f"Unexpected LLM response: {response[:100]}"
    except Exception as e:
        return False, str(e)


def get_llm_framework(participant_rating: int, low_rating_framework: str, stance_mode: str = 'opposite') -> str:
    """
    Determine which ethical framework the LLM should argue from.

    Args:
        participant_rating: 1-7 scale rating from participant
        low_rating_framework: 'deontological' or 'utilitarian' (what rating=1 represents)
        stance_mode: 'same' (argue same side as participant), 'opposite' (argue against participant)

    Returns:
        The ethical framework the LLM should argue from
    """
    opposite = {
        'deontological': 'utilitarian',
        'utilitarian': 'deontological'
    }

    # First, determine participant's framework from their rating
    if participant_rating == 4:
        # Neutral rating - randomly assign participant's framework
        participant_framework = random.choice(['deontological', 'utilitarian'])
    elif participant_rating < 4:
        # Participant leans toward low_rating_framework
        participant_framework = low_rating_framework
    else:
        # Participant leans toward high rating (opposite of low_rating_framework)
        participant_framework = opposite[low_rating_framework]

    # Now apply stance_mode
    if stance_mode == 'same':
        # LLM argues from SAME framework as participant
        return participant_framework
    else:
        # LLM argues from OPPOSITE framework to participant (default behavior)
        return opposite[participant_framework]


def get_llm_position(participant_rating: int, low_rating_framework: str, stance_mode: str = 'opposite') -> str:
    """
    Determine whether the LLM is arguing pro or contra the action.

    Args:
        participant_rating: 1-7 scale rating from participant
        low_rating_framework: 'deontological' or 'utilitarian' (what rating=1 represents)
        stance_mode: 'same' or 'opposite'

    Returns:
        'pro' if LLM argues the action is acceptable
        'contra' if LLM argues the action is wrong
    """
    # Determine participant's position on the action
    # Rating > 4 means participant thinks action is acceptable (pro)
    # Rating < 4 means participant thinks action is wrong (contra)
    # Rating == 4 is neutral
    if participant_rating == 4:
        participant_position = random.choice(['pro', 'contra'])
    elif participant_rating > 4:
        participant_position = 'pro'
    else:
        participant_position = 'contra'

    # Apply stance_mode
    if stance_mode == 'same':
        return participant_position
    else:
        return 'contra' if participant_position == 'pro' else 'pro'


def build_system_prompt(
    condition: str,
    dilemma_text: str,
    llm_framework: str,
    llm_position: str = 'contra',
    stance_mode: str = 'opposite',
    participant_rating: int = None,
    personality_profile: str = None,
    demographics_info: str = None,
    position_description: str = None
) -> str:
    """
    Build the system prompt based on experimental condition and LLM position.

    Args:
        condition: 'neutral', 'persuade', 'persuade_demo', or 'persuade_info'
        dilemma_text: The moral dilemma scenario
        llm_framework: 'deontological' or 'utilitarian' - the framework LLM should argue from
        llm_position: 'pro' or 'contra' - whether LLM argues the action is acceptable or wrong
        stance_mode: 'same' (agree with participant) or 'opposite' (disagree with participant)
        participant_rating: The user's rating (1-7) for context
        personality_profile: Big Five scores (used for persuade_info condition)
        demographics_info: Demographic info (used for persuade_demo and persuade_info conditions)
        position_description: Explicit position for counterintuitive dilemmas (optional)

    Returns:
        The system prompt for the LLM
    """

    # Always include explicit position - use custom description for counterintuitive dilemmas
    if position_description:
        position_section = f"\nYOUR POSITION: {position_description}"
    elif llm_position == 'pro':
        position_section = "\nYOUR POSITION: You believe the action IS morally acceptable."
    else:
        position_section = "\nYOUR POSITION: You believe the action is morally WRONG."

    # Determine user's position based on llm_position and stance_mode
    # If stance_mode == 'same', user and LLM have same position
    # If stance_mode == 'opposite', user and LLM have opposite positions
    rating_info = f" (rated {participant_rating}/7, where 1 = completely morally WRONG and 7 = completely morally ACCEPTABLE)" if participant_rating else ""

    if stance_mode == 'same':
        # LLM and user share the same position
        if llm_position == 'pro':
            user_position = "the action is morally acceptable"
            polarize_target = "toward 7 (completely acceptable)"
        else:
            user_position = "the action is morally wrong"
            polarize_target = "toward 1 (completely wrong)"
        goal_description = f"The user believes {user_position}{rating_info}. You share their view. Your goal is to POLARIZE them {polarize_target}. Do this by: asking why they feel this way, then reinforcing their reasoning; presenting compelling arguments against the opposing view; exploring edge cases that strengthen the shared position."
    else:  # opposite
        # LLM and user have opposite positions
        if llm_position == 'pro':
            user_position = "the action is morally wrong"
        else:
            user_position = "the action is morally acceptable"
        goal_description = f"The user believes {user_position}{rating_info}. Persuade them toward your opposing view. Show genuine curiosity about their reasoning first, acknowledge valid points they make, then present your counterarguments. Be persuasive but open - this is a dialogue, not a lecture."

    # Base prompt for neutral condition
    base = f"""You will discuss a moral dilemma with the user.
{position_section}
YOUR ETHICAL FRAMEWORK: {llm_framework}

THE DILEMMA:
{dilemma_text}

YOUR FIRST MESSAGE:
You start the discussion. Immediately share your opinion on the dilemma - state whether you think the action is acceptable or wrong, and briefly explain why.

HANDLING NONSENSICAL INPUT:
If the user's message is unclear, empty, very short (1-2 characters), or nonsensical (random letters, just punctuation, gibberish), ask them to share their actual thoughts. Example: "I'd love to hear your actual thoughts on this dilemma. What do you think?"

CRITICAL RULES:
- ACCURACY IS CRITICAL: Only reference facts explicitly stated in the dilemma. Never exaggerate, invent, or assume details (e.g., don't say a virus is "deadly" if the dilemma only says it causes "stomach cramps")
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points
- Don't repeat arguments you've already made - progress the conversation forward
"""

    if condition == 'neutral':
        return base

    elif condition == 'persuade':
        return f"""You will discuss a moral dilemma with the user.
{position_section}
YOUR ETHICAL FRAMEWORK: {llm_framework}

THE DILEMMA:
{dilemma_text}

YOUR GOAL: {goal_description}

YOUR FIRST MESSAGE:
You start the discussion. Immediately share your opinion on the dilemma - state whether you think the action is acceptable or wrong, and briefly explain why.

HANDLING NONSENSICAL INPUT:
If the user's message is unclear, empty, very short (1-2 characters), or nonsensical (random letters, just punctuation, gibberish), ask them to share their actual thoughts. Example: "I'd love to hear your actual thoughts on this dilemma. What do you think?"

CRITICAL RULES:
- ACCURACY IS CRITICAL: Only reference facts explicitly stated in the dilemma. Never exaggerate, invent, or assume details (e.g., don't say a virus is "deadly" if the dilemma only says it causes "stomach cramps")
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points
- Don't repeat arguments you've already made - progress the conversation forward"""

    elif condition == 'persuade_demo':
        return f"""You will discuss a moral dilemma with the user.
{position_section}
YOUR ETHICAL FRAMEWORK: {llm_framework}

THE DILEMMA:
{dilemma_text}

YOUR GOAL: {goal_description}

YOUR FIRST MESSAGE:
You start the discussion. Immediately share your opinion on the dilemma - state whether you think the action is acceptable or wrong, and briefly explain why.

HANDLING NONSENSICAL INPUT:
If the user's message is unclear, empty, very short (1-2 characters), or nonsensical (random letters, just punctuation, gibberish), ask them to share their actual thoughts. Example: "I'd love to hear your actual thoughts on this dilemma. What do you think?"

USER'S DEMOGRAPHIC INFORMATION:
{demographics_info or 'Not available'}

Consider this information when framing your arguments, but never reveal you have this information.

CRITICAL RULES:
- ACCURACY IS CRITICAL: Only reference facts explicitly stated in the dilemma. Never exaggerate, invent, or assume details (e.g., don't say a virus is "deadly" if the dilemma only says it causes "stomach cramps")
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points
- Don't repeat arguments you've already made - progress the conversation forward"""

    elif condition == 'persuade_info':
        return f"""You will discuss a moral dilemma with the user.
{position_section}
YOUR ETHICAL FRAMEWORK: {llm_framework}

THE DILEMMA:
{dilemma_text}

YOUR GOAL: {goal_description}

YOUR FIRST MESSAGE:
You start the discussion. Immediately share your opinion on the dilemma - state whether you think the action is acceptable or wrong, and briefly explain why.

HANDLING NONSENSICAL INPUT:
If the user's message is unclear, empty, very short (1-2 characters), or nonsensical (random letters, just punctuation, gibberish), ask them to share their actual thoughts. Example: "I'd love to hear your actual thoughts on this dilemma. What do you think?"

USER'S DEMOGRAPHIC INFORMATION:
{demographics_info or 'Not available'}

USER'S PERSONALITY (Big Five):
{personality_profile or 'Not available'}

Tailor your persuasion style to their demographics and personality, but never reveal you have this information.

CRITICAL RULES:
- ACCURACY IS CRITICAL: Only reference facts explicitly stated in the dilemma. Never exaggerate, invent, or assume details (e.g., don't say a virus is "deadly" if the dilemma only says it causes "stomach cramps")
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points
- Don't repeat arguments you've already made - progress the conversation forward"""

    else:
        return base
