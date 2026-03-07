# Multi-Claw

12 изолированных Telegram-ботов для Google Calendar, каждый на своём AI-провайдере.

## Архитектура

```
multi-claw/
├── docker-compose.yml          # 12 pods + orchestrator
├── Dockerfile                  # Orchestrator (dashboard)
├── run.py                      # FastAPI dashboard
├── SETTINGS.py
├── .env.example
├── FRONTEND/index.html         # Dashboard статусов
├── BACKEND/
│   ├── health.py               # Агрегация здоровья pods
│   ├── ai_provider.py          # Абстрактный интерфейс AI
│   ├── base_bot.py             # Telegram-бот с командами
│   ├── calendar_service.py     # Google Calendar API
│   ├── health_server.py        # HTTP /health endpoint
│   ├── ai_providers/           # 8 провайдеров
│   └── PODS/                   # 12 pod-контейнеров
│       ├── mini-claw/          # OpenAI GPT-4o
│       ├── pico-claw/          # Anthropic Claude Sonnet
│       ├── nano-claw/          # Google Gemini Flash
│       ├── tiny-claw/          # Mistral Large
│       ├── open-claw/          # OpenAI GPT-4o-mini
│       ├── zero-claw/          # Anthropic Claude Haiku
│       ├── titan-claw/         # Google Gemini Flash Lite
│       ├── kaf-claw/           # xAI Grok-2
│       ├── safe-claw/          # Anthropic Claude Opus
│       ├── null-claw/          # DeepSeek
│       ├── tinyagi/            # Groq Llama 3.1 70B
│       └── nanobot/            # Together Mixtral 8x22B
```

## Pods

| Pod | Провайдер | Модель | SDK |
|-----|-----------|--------|-----|
| mini-claw | OpenAI | gpt-4o | `openai` |
| pico-claw | Anthropic | claude-sonnet-4-6 | `anthropic` |
| nano-claw | Google | gemini-2.0-flash | `google-genai` |
| tiny-claw | Mistral | mistral-large-latest | `mistralai` |
| open-claw | OpenAI | gpt-4o-mini | `openai` |
| zero-claw | Anthropic | claude-haiku-4-5 | `anthropic` |
| titan-claw | Google | gemini-2.0-flash-lite | `google-genai` |
| kaf-claw | xAI | grok-2 | `openai` (base_url=api.x.ai) |
| safe-claw | Anthropic | claude-opus-4-6 | `anthropic` |
| null-claw | DeepSeek | deepseek-chat | `openai` (base_url=api.deepseek.com) |
| tinyagi | Groq | llama-3.1-70b-versatile | `groq` |
| nanobot | Together | Mixtral-8x22B-Instruct | `openai` (base_url=api.together.xyz) |

## Запуск

### 1. Подготовка Google Calendar

1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)
2. Создать проект (или выбрать существующий)
3. Включить **Google Calendar API** (APIs & Services > Enable APIs)
4. Создать **Service Account** (IAM & Admin > Service Accounts > Create)
5. Создать JSON-ключ для сервис-аккаунта (Keys > Add Key > JSON)
6. Скопировать содержимое JSON-файла — это будет `GOOGLE_SERVICE_ACCOUNT_JSON`
7. Открыть Google Calendar > Настройки нужного календаря > Доступ
8. Расшарить календарь на email сервис-аккаунта (из поля `client_email` в JSON) с правами **Внесение изменений**
9. Скопировать **Calendar ID** из настроек календаря — это будет `GOOGLE_CALENDAR_ID`

### 2. Создание Telegram-ботов

1. Написать [@BotFather](https://t.me/BotFather) в Telegram
2. Отправить `/newbot` — 12 раз, для каждого pod
3. Рекомендуемые имена: `mini_claw_bot`, `pico_claw_bot`, ..., `nanobot_cal_bot`
4. Сохранить полученные токены

### 3. Получение API-ключей

| Провайдер | Где получить |
|-----------|-------------|
| OpenAI | https://platform.openai.com/api-keys |
| Anthropic | https://console.anthropic.com/settings/keys |
| Google AI | https://aistudio.google.com/apikey |
| Mistral | https://console.mistral.ai/api-keys |
| xAI | https://console.x.ai/ |
| DeepSeek | https://platform.deepseek.com/api_keys |
| Groq | https://console.groq.com/keys |
| Together | https://api.together.xyz/settings/api-keys |

### 4. Настройка .env

```bash
cp .env.example .env
```

Заполнить все значения в `.env`:

```env
# Google Calendar
GOOGLE_CALENDAR_ID=abc123@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# 12 Telegram-токенов
TELEGRAM_TOKEN_MINI_CLAW=123456:ABC...
TELEGRAM_TOKEN_PICO_CLAW=234567:DEF...
# ... остальные 10

# 8 AI API-ключей
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=AI...
MISTRAL_API_KEY=...
XAI_API_KEY=xai-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
TOGETHER_API_KEY=...
```

### 5. Включение/выключение pods в SETTINGS.py

Каждый pod управляется константой `"on"` / `"off"` в `SETTINGS.py`:

```python
POD_MINI_CLAW = "on"       # OpenAI GPT-4o
POD_PICO_CLAW = "on"       # Anthropic Claude Sonnet
POD_NANO_CLAW = "on"       # Google Gemini Flash
POD_TINY_CLAW = "off"      # Mistral Large
# ... и т.д.
```

- `"on"` — pod запускается в Docker Compose, dashboard показывает его статус
- `"off"` — pod не запускается, dashboard показывает "disabled"

По умолчанию включены 3 pod: mini-claw, pico-claw, nano-claw. Включите нужные перед запуском.

### 6. Запуск через Docker Compose

```bash
# Автоматический запуск (читает SETTINGS.py, поднимает только "on" pods)
python run.py compose

# Или вручную — указать profiles для нужных pods
docker compose --profile mini-claw --profile pico-claw --profile nano-claw up -d --build

# Проверить статус
docker compose ps

# Логи конкретного pod
docker compose logs -f mini-claw

# Логи всех
docker compose logs -f

# Остановить
docker compose down
```

Dashboard доступен на http://localhost:8000

### 7. Локальный запуск (только dashboard)

```bash
pip install -r requirements.txt
python run.py
```

Dashboard запустится на http://localhost:8000, но без Docker pods будут показаны как offline/disabled.

## Команды Telegram-бота

Все 12 ботов поддерживают одинаковый набор команд:

| Команда | Действие |
|---------|----------|
| `/start` | Приветствие с именем pod и моделью |
| `/help` | Список команд |
| `/today` | События на сегодня |
| `/week` | События на неделю |
| `/new <текст>` | Создать событие из текста |
| `/delete` | Показать события для удаления |
| `/free <дата>` | Свободные слоты на дату |
| `/status` | Статус бота, модель, uptime |
| Любой текст | AI разбирает намерение и выполняет действие |

## Изоляция сети

- Каждый pod в собственной bridge-сети (`net-mini-claw`, `net-pico-claw`, ...)
- Pods не могут общаться друг с другом
- Orchestrator подключён ко всем 12 сетям для проверки health
- Каждый pod получает только свой AI API-ключ

## Healthcheck

- Каждый pod запускает HTTP-сервер на `:5000` с endpoint `/health`
- Docker healthcheck опрашивает `/health` каждые 15 секунд
- Dashboard автоматически обновляет статусы каждые 10 секунд

## Верификация

```bash
# 1. Включить нужные pods в SETTINGS.py, затем запустить
python run.py compose

# 2. Проверить что enabled pods стартовали и прошли healthcheck
docker compose ps  # enabled pods должны быть healthy

# 3. Отправить /status каждому боту — ответ с именем модели
# 4. Отправить /today — список событий из календаря
# 5. Проверить изоляцию:
docker compose exec mini-claw ping -c1 pico-claw  # должен упасть
```
