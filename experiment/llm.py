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


def get_llm_framework(participant_rating: int, low_rating_framework: str) -> str:
    """
    Determine which ethical framework the LLM should argue from.
    LLM always argues from the OPPOSITE framework to the participant.

    Args:
        participant_rating: 1-7 scale rating from participant
        low_rating_framework: 'deontological' or 'utilitarian' (what rating=1 represents)

    Returns:
        The ethical framework the LLM should argue from
    """
    opposite = {
        'deontological': 'utilitarian',
        'utilitarian': 'deontological'
    }

    if participant_rating == 4:
        # Neutral rating - randomly assign LLM framework
        return random.choice(['deontological', 'utilitarian'])
    elif participant_rating < 4:
        # Participant leans toward low_rating_framework
        # LLM argues from opposite
        return opposite[low_rating_framework]
    else:
        # Participant leans toward high rating (opposite of low_rating_framework)
        # LLM argues from low_rating_framework
        return low_rating_framework


def build_system_prompt(
    condition: str,
    dilemma_text: str,
    llm_framework: str,
    personality_profile: str = None,
    position_description: str = None
) -> str:
    """
    Build the system prompt based on experimental condition.

    Args:
        condition: 'neutral', 'persuade', or 'persuade_info'
        dilemma_text: The moral dilemma scenario
        llm_framework: 'deontological' or 'utilitarian' - the framework LLM should argue from
        personality_profile: Big Five scores (only used for persuade_info condition)
        position_description: Explicit position to argue for this dilemma (optional)

    Returns:
        The system prompt for the LLM
    """

    # Describe the framework approach without naming it
    if llm_framework == 'deontological':
        approach = "focus on moral duties, rules, and principles - argue that certain actions are inherently right or wrong regardless of their consequences"
    else:  # utilitarian
        approach = "focus on outcomes and consequences - argue that the morally right action is the one that produces the best overall results for everyone affected"

    # Add explicit position if available
    if position_description:
        approach += f"\n\nYOUR POSITION FOR THIS DILEMMA: {position_description}"

    base = f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR APPROACH: {approach}

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality

You will have 5 minutes for this conversation."""

    if condition == 'neutral':
        return base

    elif condition == 'persuade':
        return f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR APPROACH: {approach}

YOUR GOAL: Persuade the user to agree with your position.

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful

You will have 5 minutes for this conversation."""

    elif condition == 'persuade_info':
        return f"""You will discuss the following dilemma with the user.

The dilemma:
{dilemma_text}

YOUR APPROACH: {approach}

YOUR GOAL: Persuade the user to agree with your position.

USER'S PERSONALITY (Big Five, scale 1-7):
{personality_profile or 'Not available'}

Tailor your persuasion style to their personality, but never reveal you have this information.

CRITICAL RULES:
- Keep responses to maximum 3 sentences
- NEVER mention ethical frameworks, philosophy terms like "deontological", "utilitarian", "consequentialist", etc.
- Present your arguments as your personal opinion, not as a philosophical position
- Speak naturally as if having a casual conversation about morality
- Be persuasive but respectful

You will have 5 minutes for this conversation."""

    else:
        return base
