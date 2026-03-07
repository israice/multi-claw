from openai import AsyncOpenAI
from BACKEND.ai_provider import AIProvider


class DeepSeekProvider(AIProvider):
    """DeepSeek provider (OpenAI-compatible API)."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

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
        return "DeepSeek"
