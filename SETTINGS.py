import os

APP_TITLE = "Multi-Claw Dashboard"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", 8000))
RELOAD = True
LIVE_RELOAD = True
LIVE_RELOAD_INTERVAL = 5

# ═══════════════════════════════════════════════════════════════
# PODS ON/OFF — включить/выключить отдельные pods
# "on"  = pod запускается в docker compose
# "off" = pod не запускается, dashboard показывает "disabled"
# ═══════════════════════════════════════════════════════════════

POD_MINI_CLAW = "on"       # OpenAI GPT-4o
POD_PICO_CLAW = "on"       # Anthropic Claude Sonnet
POD_NANO_CLAW = "on"       # Google Gemini Flash
POD_TINY_CLAW = "off"      # Mistral Large
POD_OPEN_CLAW = "off"      # OpenAI GPT-4o-mini
POD_ZERO_CLAW = "off"      # Anthropic Claude Haiku
POD_TITAN_CLAW = "off"     # Google Gemini Flash Lite
POD_KAF_CLAW = "off"       # xAI Grok-2
POD_SAFE_CLAW = "off"      # Anthropic Claude Opus
POD_NULL_CLAW = "off"      # DeepSeek
POD_TINYAGI = "off"        # Groq Llama 3.1 70B
POD_NANOBOT = "off"        # Together Mixtral 8x22B

# Реестр: имя pod → константа
PODS_REGISTRY = {
    "mini-claw":  POD_MINI_CLAW,
    "pico-claw":  POD_PICO_CLAW,
    "nano-claw":  POD_NANO_CLAW,
    "tiny-claw":  POD_TINY_CLAW,
    "open-claw":  POD_OPEN_CLAW,
    "zero-claw":  POD_ZERO_CLAW,
    "titan-claw": POD_TITAN_CLAW,
    "kaf-claw":   POD_KAF_CLAW,
    "safe-claw":  POD_SAFE_CLAW,
    "null-claw":  POD_NULL_CLAW,
    "tinyagi":    POD_TINYAGI,
    "nanobot":    POD_NANOBOT,
}
