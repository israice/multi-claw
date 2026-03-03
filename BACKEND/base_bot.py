import asyncio
import json
import logging
import time
from datetime import datetime, timedelta

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from BACKEND.ai_provider import AIProvider, SYSTEM_PROMPT
from BACKEND.calendar_service import CalendarService
from BACKEND.health_server import HealthServer

logger = logging.getLogger(__name__)


class BaseBot:
    """Telegram bot with calendar commands, powered by a pluggable AI provider."""

    def __init__(self, token: str, pod_name: str, ai: AIProvider, health_port: int = 8080):
        self.token = token
        self.pod_name = pod_name
        self.ai = ai
        self.calendar = CalendarService()
        self.health = HealthServer(port=health_port)
        self.start_time = time.time()

    def _system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            pod_name=self.pod_name,
            model_name=self.ai.model,
            today=datetime.utcnow().strftime("%Y-%m-%d"),
        )

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"👋 Привет! Я **{self.pod_name}**\n"
            f"🤖 Модель: `{self.ai.model}` ({self.ai.provider_name})\n\n"
            f"Я помогу управлять Google Calendar.\n"
            f"Отправь /help для списка команд.",
            parse_mode="Markdown",
        )

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📋 **Команды:**\n"
            "/today — события на сегодня\n"
            "/week — события на неделю\n"
            "/new <текст> — создать событие\n"
            "/delete — удалить событие\n"
            "/free <дата> — свободные слоты\n"
            "/status — статус бота\n\n"
            "Или просто напиши что нужно — AI разберётся!",
            parse_mode="Markdown",
        )

    async def cmd_today(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        try:
            events = await asyncio.to_thread(self.calendar.list_events, today, today)
            if not events:
                await update.message.reply_text("📅 Сегодня нет событий.")
                return
            lines = [f"📅 **События на {today}:**\n"]
            for e in events:
                start = e["start"].split("T")[1][:5] if "T" in e["start"] else "весь день"
                lines.append(f"• {start} — {e['title']}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as ex:
            logger.exception("cmd_today error")
            await update.message.reply_text(f"❌ Ошибка: {ex}")

    async def cmd_week(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        today = datetime.utcnow()
        start = today.strftime("%Y-%m-%d")
        end = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            events = await asyncio.to_thread(self.calendar.list_events, start, end)
            if not events:
                await update.message.reply_text("📅 На этой неделе нет событий.")
                return
            lines = [f"📅 **События {start} — {end}:**\n"]
            for e in events:
                day = e["start"][:10]
                t = e["start"].split("T")[1][:5] if "T" in e["start"] else ""
                lines.append(f"• {day} {t} — {e['title']}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as ex:
            logger.exception("cmd_week error")
            await update.message.reply_text(f"❌ Ошибка: {ex}")

    async def cmd_new(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.replace("/new", "").strip()
        if not text:
            await update.message.reply_text("Опиши событие, например:\n`/new Встреча с Иваном завтра в 14:00`", parse_mode="Markdown")
            return
        await self._process_with_ai(update, f"Create a calendar event: {text}")

    async def cmd_delete(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        end = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            events = await asyncio.to_thread(self.calendar.list_events, today, end)
            if not events:
                await update.message.reply_text("Нет событий для удаления.")
                return
            lines = ["Какое событие удалить? Напиши ID:\n"]
            for e in events:
                lines.append(f"`{e['id'][:8]}` — {e['title']} ({e['start'][:10]})")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as ex:
            logger.exception("cmd_delete error")
            await update.message.reply_text(f"❌ Ошибка: {ex}")

    async def cmd_free(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.replace("/free", "").strip()
        date = text if text else datetime.utcnow().strftime("%Y-%m-%d")
        try:
            slots = await asyncio.to_thread(self.calendar.find_free_slots, date)
            if not slots:
                await update.message.reply_text(f"🕐 Нет свободных слотов на {date}.")
                return
            lines = [f"🕐 **Свободные слоты на {date}:**\n"]
            for s in slots:
                lines.append(f"• {s['start']} — {s['end']}")
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as ex:
            logger.exception("cmd_free error")
            await update.message.reply_text(f"❌ Ошибка: {ex}")

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uptime = int(time.time() - self.start_time)
        h, m = divmod(uptime // 60, 60)
        s = uptime % 60
        await update.message.reply_text(
            f"🤖 **{self.pod_name}**\n"
            f"Провайдер: {self.ai.provider_name}\n"
            f"Модель: `{self.ai.model}`\n"
            f"Uptime: {h}h {m}m {s}s\n"
            f"Статус: ✅ работает",
            parse_mode="Markdown",
        )

    async def handle_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if not text:
            return
        await self._process_with_ai(update, text)

    async def _process_with_ai(self, update: Update, text: str):
        try:
            response = await self.ai.chat(text, self._system_prompt())
            parsed = self._try_parse_action(response)

            if parsed and parsed.get("action") == "create":
                result = await asyncio.to_thread(
                    self.calendar.create_event,
                    parsed["title"],
                    parsed["date"],
                    parsed["start_time"],
                    parsed["end_time"],
                    parsed.get("description", ""),
                )
                await update.message.reply_text(f"✅ Создано: **{result['title']}**\n🔗 {result.get('link', '')}", parse_mode="Markdown")

            elif parsed and parsed.get("action") == "list":
                events = await asyncio.to_thread(
                    self.calendar.list_events,
                    parsed["start_date"],
                    parsed["end_date"],
                )
                if not events:
                    await update.message.reply_text("Нет событий за указанный период.")
                else:
                    lines = []
                    for e in events:
                        lines.append(f"• {e['start'][:16]} — {e['title']}")
                    await update.message.reply_text("\n".join(lines))

            elif parsed and parsed.get("action") == "free":
                slots = await asyncio.to_thread(self.calendar.find_free_slots, parsed["date"])
                if not slots:
                    await update.message.reply_text("Нет свободных слотов.")
                else:
                    lines = [f"🕐 Свободно на {parsed['date']}:"]
                    for s in slots:
                        lines.append(f"• {s['start']} — {s['end']}")
                    await update.message.reply_text("\n".join(lines))

            elif parsed and parsed.get("action") == "delete":
                eid = parsed.get("event_id", "")
                if eid:
                    await asyncio.to_thread(self.calendar.delete_event, eid)
                    await update.message.reply_text("🗑 Событие удалено.")
                else:
                    await update.message.reply_text("Укажи ID события для удаления.")

            else:
                msg = parsed.get("message", response) if parsed else response
                await update.message.reply_text(msg)

        except Exception as ex:
            logger.exception("AI processing error")
            await update.message.reply_text(f"❌ Ошибка AI: {ex}")

    @staticmethod
    def _try_parse_action(response: str) -> dict | None:
        text = response.strip()
        # Try to extract JSON from markdown code blocks
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    try:
                        return json.loads(block)
                    except json.JSONDecodeError:
                        continue
        # Try direct JSON parse
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return None

    async def run(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        logger.info(f"Starting {self.pod_name} with {self.ai.provider_name}/{self.ai.model}")

        await self.health.start()
        logger.info(f"Health server on :8080")

        app = Application.builder().token(self.token).build()

        commands = [
            BotCommand("start", "Приветствие"),
            BotCommand("help", "Список команд"),
            BotCommand("today", "События на сегодня"),
            BotCommand("week", "События на неделю"),
            BotCommand("new", "Создать событие"),
            BotCommand("delete", "Удалить событие"),
            BotCommand("free", "Свободные слоты"),
            BotCommand("status", "Статус бота"),
        ]

        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("today", self.cmd_today))
        app.add_handler(CommandHandler("week", self.cmd_week))
        app.add_handler(CommandHandler("new", self.cmd_new))
        app.add_handler(CommandHandler("delete", self.cmd_delete))
        app.add_handler(CommandHandler("free", self.cmd_free))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        async with app:
            await app.bot.set_my_commands(commands)
            await app.start()
            logger.info(f"{self.pod_name} is running!")
            await app.updater.start_polling()

            # Keep running
            try:
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                pass
            finally:
                await app.updater.stop()
                await app.stop()
