from anthropic import AsyncAnthropic
from BACKEND.ai_provider import AIProvider


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(self, message: str, system_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        )
        return response.content[0].text

    @property
    def provider_name(self) -> str:
        return "Anthropic"
