import os

APP_TITLE = "Multi-Claw Dashboard"
TELEGRAM_GROUP_NICKNAME = "test"  # группа будет multi-claw-test
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))
RELOAD = False
LIVE_RELOAD = False
LIVE_RELOAD_INTERVAL = 5

# ═══════════════════════════════════════════════════════════════
# PODS ON/OFF
# ═══════════════════════════════════════════════════════════════
MINI_CLAW_ENABLED   = "on"
PICO_CLAW_ENABLED   = "on"
NANO_CLAW_ENABLED   = "off"
TINY_CLAW_ENABLED   = "off"
OPEN_CLAW_ENABLED   = "off"
ZERO_CLAW_ENABLED   = "off"
TITAN_CLAW_ENABLED  = "off"
KAF_CLAW_ENABLED    = "off"
SAFE_CLAW_ENABLED   = "off"
NULL_CLAW_ENABLED   = "off"
TINYAGI_ENABLED     = "off"
NANOBOT_ENABLED     = "off"

# ═══════════════════════════════════════════════════════════════
# PODS — меняй ТОЛЬКО provider ключ, остальное подтянется само
# ═══════════════════════════════════════════════════════════════
MINI_CLAW_PROVIDER  = "GROQ_API_KEY"
PICO_CLAW_PROVIDER  = "GROQ_API_KEY"
NANO_CLAW_PROVIDER  = "GOOGLE_AI_API_KEY"
TINY_CLAW_PROVIDER  = "MISTRAL_API_KEY"
OPEN_CLAW_PROVIDER  = "OPENAI_API_KEY"
ZERO_CLAW_PROVIDER  = "ANTHROPIC_API_KEY"
TITAN_CLAW_PROVIDER = "GOOGLE_AI_API_KEY"
KAF_CLAW_PROVIDER   = "XAI_API_KEY"
SAFE_CLAW_PROVIDER  = "ANTHROPIC_API_KEY"
NULL_CLAW_PROVIDER  = "DEEPSEEK_API_KEY"
TINYAGI_PROVIDER    = "GROQ_API_KEY"
NANOBOT_PROVIDER    = "TOGETHER_API_KEY"

# ═══════════════════════════════════════════════════════════════
# PODS TOPIC ID — ID топика в группе (None = отвечает везде)
# Чтобы узнать ID: добавь бота в группу, напиши в нужном топике,
# в логах будет message_thread_id
# ═══════════════════════════════════════════════════════════════
MINI_CLAW_TOPIC_ID  = 2
PICO_CLAW_TOPIC_ID  = 6
NANO_CLAW_TOPIC_ID  = None
TINY_CLAW_TOPIC_ID  = None
OPEN_CLAW_TOPIC_ID  = None
ZERO_CLAW_TOPIC_ID  = None
TITAN_CLAW_TOPIC_ID = None
KAF_CLAW_TOPIC_ID   = None
SAFE_CLAW_TOPIC_ID  = None
NULL_CLAW_TOPIC_ID  = None
TINYAGI_TOPIC_ID    = None
NANOBOT_TOPIC_ID    = None

# ═══════════════════════════════════════════════════════════════
# PROVIDERS — api_key_env → (provider, default model)
#
# Доступные модели для замены:
#   GOOGLE_AI_API_KEY   : gemini-2.0-flash, gemini-2.0-flash-lite, gemini-2.5-flash-preview-05-20, gemini-2.5-pro-preview-05-06
#   ANTHROPIC_API_KEY   : claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-6
#   OPENAI_API_KEY      : gpt-4o-mini, gpt-4o, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, o4-mini
#   MISTRAL_API_KEY     : mistral-large-latest, mistral-small-latest, mistral-medium-latest, codestral-latest
#   XAI_API_KEY         : grok-2, grok-3, grok-3-mini
#   DEEPSEEK_API_KEY    : deepseek-chat, deepseek-reasoner
#   GROQ_API_KEY        : llama-3.3-70b-versatile, llama-3.1-8b-instant, gemma2-9b-it, mixtral-8x7b-32768
#   TOGETHER_API_KEY    : mistralai/Mixtral-8x22B-Instruct-v0.1, meta-llama/Llama-3.3-70B-Instruct-Turbo, google/gemma-2-27b-it
# ═══════════════════════════════════════════════════════════════
PROVIDERS = {
    "GOOGLE_AI_API_KEY":  ("google",    "gemini-2.0-flash"),
    "ANTHROPIC_API_KEY":  ("anthropic", "claude-haiku-4-5-20251001"),
    "OPENAI_API_KEY":     ("openai",    "gpt-4o-mini"),
    "MISTRAL_API_KEY":    ("mistral",   "mistral-large-latest"),
    "XAI_API_KEY":        ("xai",       "grok-2"),
    "DEEPSEEK_API_KEY":   ("deepseek",  "deepseek-chat"),
    "GROQ_API_KEY":       ("groq",      "llama-3.3-70b-versatile"),
    "TOGETHER_API_KEY":   ("together",  "mistralai/Mixtral-8x22B-Instruct-v0.1"),
}


# ═══════════════════════════════════════════════════════════════
# AUTO-GENERATED — не трогать руками
# ═══════════════════════════════════════════════════════════════
_PODS_RAW = {
    "mini-claw":  (MINI_CLAW_ENABLED,  MINI_CLAW_PROVIDER,  "Lightweight",    MINI_CLAW_TOPIC_ID),
    "pico-claw":  (PICO_CLAW_ENABLED,  PICO_CLAW_PROVIDER,  "Lightweight",    PICO_CLAW_TOPIC_ID),
    "nano-claw":  (NANO_CLAW_ENABLED,  NANO_CLAW_PROVIDER,  "Lightweight",    NANO_CLAW_TOPIC_ID),
    "tiny-claw":  (TINY_CLAW_ENABLED,  TINY_CLAW_PROVIDER,  "Lightweight",    TINY_CLAW_TOPIC_ID),
    "open-claw":  (OPEN_CLAW_ENABLED,  OPEN_CLAW_PROVIDER,  "Full Runtime",   OPEN_CLAW_TOPIC_ID),
    "zero-claw":  (ZERO_CLAW_ENABLED,  ZERO_CLAW_PROVIDER,  "Full Runtime",   ZERO_CLAW_TOPIC_ID),
    "titan-claw": (TITAN_CLAW_ENABLED, TITAN_CLAW_PROVIDER, "Full Runtime",   TITAN_CLAW_TOPIC_ID),
    "kaf-claw":   (KAF_CLAW_ENABLED,   KAF_CLAW_PROVIDER,   "Full Runtime",   KAF_CLAW_TOPIC_ID),
    "safe-claw":  (SAFE_CLAW_ENABLED,  SAFE_CLAW_PROVIDER,  "Security",       SAFE_CLAW_TOPIC_ID),
    "null-claw":  (NULL_CLAW_ENABLED,  NULL_CLAW_PROVIDER,  "Security",       NULL_CLAW_TOPIC_ID),
    "tinyagi":    (TINYAGI_ENABLED,    TINYAGI_PROVIDER,    "Experimental",   TINYAGI_TOPIC_ID),
    "nanobot":    (NANOBOT_ENABLED,    NANOBOT_PROVIDER,    "Experimental",   NANOBOT_TOPIC_ID),
}

PODS_CONFIG = {}
for _name, (_enabled, _key_env, _category, _topic_id) in _PODS_RAW.items():
    _provider, _model = PROVIDERS[_key_env]
    PODS_CONFIG[_name] = {
        "enabled": _enabled,
        "provider": _provider,
        "model": _model,
        "api_key_env": _key_env,
        "category": _category,
        "topic_id": _topic_id,
    }

PODS_REGISTRY = {name: cfg["enabled"] for name, cfg in PODS_CONFIG.items()}
