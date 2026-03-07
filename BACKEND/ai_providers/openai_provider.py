from openai import AsyncOpenAI
from BACKEND.ai_provider import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider."""

    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        super().__init__(model, api_key)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)

    async def chat(self, messages: list[dict], system_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    @property
    def provider_name(self) -> str:
        return "OpenAI"
