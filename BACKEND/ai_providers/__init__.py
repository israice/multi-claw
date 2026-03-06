# Providers are loaded dynamically via BACKEND.provider_factory.create_provider().
# Each provider class lives in its own module (e.g., openai_provider.py).
# Lazy imports ensure only the required SDK is loaded at runtime.
