import importlib

from BACKEND.ai_provider import AIProvider

# provider name → (module path, class name)
_PROVIDERS = {
    "openai":    ("BACKEND.ai_providers.openai_provider",    "OpenAIProvider"),
    "anthropic": ("BACKEND.ai_providers.anthropic_provider",  "AnthropicProvider"),
    "google":    ("BACKEND.ai_providers.google_provider",     "GoogleProvider"),
    "mistral":   ("BACKEND.ai_providers.mistral_provider",    "MistralProvider"),
    "deepseek":  ("BACKEND.ai_providers.deepseek_provider",   "DeepSeekProvider"),
    "groq":      ("BACKEND.ai_providers.groq_provider",       "GroqProvider"),
    "together":  ("BACKEND.ai_providers.together_provider",   "TogetherProvider"),
    "xai":       ("BACKEND.ai_providers.xai_provider",        "XAIProvider"),
}


def create_provider(provider_name: str, model: str, api_key: str) -> AIProvider:
    """Create an AI provider instance by name (lazy import)."""
    if provider_name not in _PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider_name!r}. "
            f"Available: {', '.join(sorted(_PROVIDERS))}"
        )

    module_path, class_name = _PROVIDERS[provider_name]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(model=model, api_key=api_key)
