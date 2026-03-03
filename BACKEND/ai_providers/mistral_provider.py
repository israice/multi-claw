from mistralai import Mistral
from BACKEND.ai_provider import AIProvider


class MistralProvider(AIProvider):
    """Mistral AI provider."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        self.client = Mistral(api_key=api_key)

    async def chat(self, message: str, system_prompt: str) -> str:
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""

    @property
    def provider_name(self) -> str:
        return "Mistral"
