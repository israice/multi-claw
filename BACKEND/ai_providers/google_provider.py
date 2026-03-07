from google import genai
from google.genai import types
from BACKEND.ai_provider import AIProvider


class GoogleProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, model: str, api_key: str):
        super().__init__(model, api_key)
        self.client = genai.Client(api_key=api_key)

    async def chat(self, messages: list[dict], system_prompt: str) -> str:
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        return response.text or ""

    @property
    def provider_name(self) -> str:
        return "Google"
