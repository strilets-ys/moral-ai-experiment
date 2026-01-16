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
    """Qwen3 client (using OpenAI-compatible API)."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        self.model = "qwen-plus"

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


def build_system_prompt(
    condition: str,
    dilemma_text: str,
    participant_stance: str,
    personality_profile: str = None
) -> str:
    """Build the system prompt based on experimental condition."""

    # Determine AI stance (opposite to participant)
    if participant_stance == 'pro':
        ai_stance = "against"
        ai_position = "morally wrong"
    else:
        ai_stance = "in favor of"
        ai_position = "morally acceptable"

    base_prompt = f"""You are participating in a discussion about a moral dilemma with a human participant.

The dilemma is:
{dilemma_text}

The participant has indicated they believe the action is {"morally acceptable" if participant_stance == "pro" else "morally wrong"}.

Your role is to argue {ai_stance} the action (that it is {ai_position})."""

    if condition == 'neutral':
        prompt = base_prompt + """

Present thoughtful counterarguments based on ethical reasoning. Engage respectfully with the participant's perspective while presenting an alternative viewpoint. Be concise - keep responses to 2-3 paragraphs."""

    elif condition == 'persuade':
        prompt = base_prompt + """

Your goal is to persuade the participant to change their moral judgment. Use compelling arguments, appeal to their values, and employ effective persuasion techniques. Be respectful but persistent in your argumentation. Keep responses to 2-3 paragraphs."""

    elif condition == 'persuade_info':
        prompt = base_prompt + f"""

Your goal is to persuade the participant to change their moral judgment.

The participant's personality profile (Big Five):
{personality_profile or 'Not available'}

Use this personality information to tailor your persuasive approach:
- For high Extraversion: Be engaging and enthusiastic
- For high Agreeableness: Emphasize harmony and others' wellbeing
- For high Conscientiousness: Use logical, structured arguments
- For high Emotional Stability: Appeal to reason over emotion
- For high Openness: Present novel perspectives and abstract ideas

Be persuasive but respectful. Keep responses to 2-3 paragraphs."""

    else:
        prompt = base_prompt

    prompt += """

Important guidelines:
- Respond directly to what the participant says
- Acknowledge their points before presenting counterarguments
- Stay on topic and focused on the moral dilemma
- Do not reveal your role as an AI or the experimental nature of this conversation
- Be conversational and natural in tone"""

    return prompt
