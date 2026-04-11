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
        self.model = "claude-sonnet-4-20250514"

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


def get_llm_client(provider: str) -> BaseLLMClient:
    """Factory function to get appropriate LLM client."""
    clients = {
        'openai': OpenAIClient,
        'anthropic': AnthropicClient,
        'qwen': QwenClient,
    }

    client_class = clients.get(provider, OpenAIClient)
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
    personality_profile: str = None,
    position_description: str = None
) -> str:
    """
    Build the system prompt based on experimental condition and LLM position.

    Args:
        condition: 'neutral', 'persuade', or 'persuade_info'
        dilemma_text: The moral dilemma scenario
        llm_framework: 'deontological' or 'utilitarian' - the framework LLM should argue from
        llm_position: 'pro' (same as participant - polarize) or 'contra' (opposite - persuade to change)
        personality_profile: Big Five scores (only used for persuade_info condition)
        position_description: Explicit position for counterintuitive dilemmas (optional)

    Returns:
        The system prompt for the LLM
    """

    # For counterintuitive dilemmas, include explicit position guidance
    position_section = ""
    if position_description:
        position_section = f"\n\nYOUR POSITION: {position_description}"

    # Define the goal based on position
    # contra = opposite to participant -> persuade them to change their mind
    # pro = same as participant -> take extreme position to polarize
    if llm_position == 'pro':
        goal_description = "Reinforce and strengthen the user's existing position by presenting the most compelling arguments for your shared view. Take a strong, confident stance to validate and amplify their opinion."
    else:  # contra
        goal_description = "Persuade the user to reconsider their position and move toward your opposing view. Challenge their assumptions respectfully but firmly."

    # Base prompt for neutral condition
    base = f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR ETHICAL FRAMEWORK: {llm_framework}{position_section}

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points
"""

    if condition == 'neutral':
        return base

    elif condition == 'persuade':
        return f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR ETHICAL FRAMEWORK: {llm_framework}{position_section}

YOUR GOAL: {goal_description}

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points"""

    elif condition == 'persuade_info':
        return f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR ETHICAL FRAMEWORK: {llm_framework}{position_section}

YOUR GOAL: {goal_description}

USER'S PERSONALITY (Big Five, scale 1-7):
{personality_profile or 'Not available'}

Tailor your persuasion style to their personality, but never reveal you have this information.

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful
- Engage directly with the user's responses - acknowledge, respond to, or build upon what they say before making your own points"""

    else:
        return base
