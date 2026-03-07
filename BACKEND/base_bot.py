import asyncio
import collections
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from BACKEND.ai_provider import AIProvider, SYSTEM_PROMPT
from BACKEND.calendar_service import CalendarService
from BACKEND.health_server import HealthServer

logger = logging.getLogger(__name__)

def _parse_allow_from() -> set[int]:
    raw = os.environ.get("TELEGRAM_ALLOW_FROM", "").strip()
    if not raw:
        return set()
    return {int(uid.strip()) for uid in raw.split(",") if uid.strip()}


class BaseBot:
    """Telegram bot with calendar commands, powered by a pluggable AI provider."""

    def __init__(self, token: str, pod_name: str, ai: AIProvider, health_port: int = 5000, topic_id: int | None = None):
        self.token = token
        self.pod_name = pod_name
        self.ai = ai
        self.topic_id = topic_id
        self.allowed_users = _parse_allow_from()
        self.calendar = CalendarService()
        self.health = HealthServer(port=health_port)
        self.start_time = time.time()
        self._history: dict[int, list[dict]] = collections.defaultdict(list)
        self._max_history = 20

    def _is_allowed(self, update: Update) -> bool:
        """Check if user is in TELEGRAM_ALLOW_FROM (empty = allow all)."""
        if not self.allowed_users:
            return True
        user = update.effective_user
        if not user or user.id not in self.allowed_users:
            uid = user.id if user else "?"
            logger.warning(f"[{self.pod_name}] blocked user_id={uid} (not in TELEGRAM_ALLOW_FROM)")
            return False
        return True

    def _is_my_topic(self, update: Update) -> bool:
        """Check if message belongs to the configured topic (or no filter set)."""
        if not self._is_allowed(update):
            return False
        if self.topic_id is None:
            return True
        return getattr(update.message, "message_thread_id", None) == self.topic_id

    def _system_prompt(self) -> str:
        tz_name = os.environ.get("CALENDAR_TIMEZONE", "UTC")
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now = datetime.utcnow()
        return SYSTEM_PROMPT.format(
            pod_name=self.pod_name,
            model_name=self.ai.model,
            now=now.strftime("%Y-%m-%d %H:%M"),
            timezone=tz_name,
        )

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_my_topic(update):
            return
        await update.message.reply_text(
            f"👋 Привет! Я **{self.pod_name}**\n"
            f"🤖 Модель: `{self.ai.model}` ({self.ai.provider_name})\n\n"
            f"Я помогу управлять Google Calendar.\n"
            f"Отправь /help для списка команд.",
            parse_mode="Markdown",
        )

    async def cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_my_topic(update):
            return
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
        if not self._is_my_topic(update):
            return
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
        if not self._is_my_topic(update):
            return
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
        if not self._is_my_topic(update):
            return
        text = update.message.text.replace("/new", "").strip()
        if not text:
            await update.message.reply_text("Опиши событие, например:\n`/new Встреча с Иваном завтра в 14:00`", parse_mode="Markdown")
            return
        await self._process_with_ai(update, f"Create a calendar event: {text}")

    async def cmd_delete(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_my_topic(update):
            return
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
        if not self._is_my_topic(update):
            return
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
        if not self._is_my_topic(update):
            return
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
        thread_id = getattr(update.message, "message_thread_id", None)
        if thread_id:
            logger.info(f"[{self.pod_name}] message_thread_id={thread_id}")
        if not self._is_my_topic(update):
            return
        text = update.message.text
        if not text:
            return
        await self._process_with_ai(update, text)

    async def _process_with_ai(self, update: Update, text: str):
        chat_id = update.effective_chat.id if update.effective_chat else 0
        history = self._history[chat_id]
        history.append({"role": "user", "content": text})
        if len(history) > self._max_history:
            history[:] = history[-self._max_history:]

        try:
            response = await self.ai.chat(history, self._system_prompt())

            actions = self._parse_actions(response)
            if not actions:
                history.append({"role": "assistant", "content": response})
                await update.message.reply_text(response)
                return

            chat_parts = []
            created = []
            for parsed in actions:
                action = parsed.get("action")

                if action == "create":
                    try:
                        result = await asyncio.to_thread(
                            self.calendar.create_event,
                            title=parsed["title"],
                            date=parsed.get("date", ""),
                            start_time=parsed.get("start_time", ""),
                            end_time=parsed.get("end_time", ""),
                            description=parsed.get("description", ""),
                            location=parsed.get("location", ""),
                            attendees=parsed.get("attendees"),
                            recurrence=parsed.get("recurrence"),
                            reminders_minutes=parsed.get("reminders_minutes"),
                            all_day=parsed.get("all_day", False),
                        )
                        time_str = f"{parsed['start_time']}-{parsed['end_time']} " if parsed.get("start_time") else ""
                        created.append(f"[{result['id']}] {time_str}{result['title']}")
                    except Exception as ex:
                        logger.exception("create_event error")
                        created.append(f"❌ {parsed.get('title', '?')}: {ex}")

                elif action == "update":
                    eid = parsed.get("event_id", "")
                    if not eid or not eid.isascii() or " " in eid:
                        chat_parts.append("❌ Нет валидного event_id для обновления. Сначала выведи список (/today или list).")
                        continue
                    try:
                        result = await asyncio.to_thread(
                            self.calendar.update_event,
                            event_id=eid,
                            title=parsed.get("title", ""),
                            description=parsed.get("description", ""),
                            date=parsed.get("date", ""),
                            start_time=parsed.get("start_time", ""),
                            end_time=parsed.get("end_time", ""),
                            location=parsed.get("location", ""),
                            attendees=parsed.get("attendees"),
                            recurrence=parsed.get("recurrence"),
                            reminders_minutes=parsed.get("reminders_minutes"),
                            all_day=parsed.get("all_day"),
                        )
                        chat_parts.append(f"✏️ Обновлено: {result['title']}")
                    except Exception as ex:
                        logger.exception("update_event error")
                        chat_parts.append(f"❌ Ошибка обновления: {ex}")

                elif action == "list":
                    events = await asyncio.to_thread(
                        self.calendar.list_events,
                        parsed["start_date"],
                        parsed["end_date"],
                        parsed.get("query", ""),
                    )
                    if not events:
                        chat_parts.append("Нет событий за указанный период.")
                    else:
                        lines = []
                        for e in events:
                            parts = [f"• [{e['id']}] {e['start'][:16]} — {e['title']}"]
                            if e.get("location"):
                                parts[0] += f" 📍{e['location']}"
                            lines.append(parts[0])
                        chat_parts.append("\n".join(lines))

                elif action == "get":
                    try:
                        e = await asyncio.to_thread(self.calendar.get_event, parsed["event_id"])
                        info = [f"📅 {e['title']}"]
                        info.append(f"Начало: {e['start']}")
                        info.append(f"Конец: {e['end']}")
                        if e.get("description"):
                            info.append(f"Описание: {e['description']}")
                        if e.get("location"):
                            info.append(f"Место: {e['location']}")
                        if e.get("attendees"):
                            info.append(f"Участники: {', '.join(e['attendees'])}")
                        chat_parts.append("\n".join(info))
                    except Exception as ex:
                        chat_parts.append(f"❌ Событие не найдено: {ex}")

                elif action == "quick_add":
                    try:
                        result = await asyncio.to_thread(self.calendar.quick_add, parsed["text"])
                        chat_parts.append(f"✅ Создано: {result['title']} ({result['start']})")
                    except Exception as ex:
                        chat_parts.append(f"❌ Ошибка quickAdd: {ex}")

                elif action == "free":
                    slots = await asyncio.to_thread(self.calendar.find_free_slots, parsed["date"])
                    if not slots:
                        chat_parts.append("Нет свободных слотов.")
                    else:
                        lines = [f"🕐 Свободно на {parsed['date']}:"]
                        lines += [f"• {s['start']} — {s['end']}" for s in slots]
                        chat_parts.append("\n".join(lines))

                elif action == "delete":
                    eid = parsed.get("event_id", "")
                    if eid and eid.isascii() and " " not in eid:
                        try:
                            await asyncio.to_thread(self.calendar.delete_event, eid)
                            chat_parts.append(f"🗑 Удалено: {eid}")
                        except Exception as ex:
                            chat_parts.append(f"❌ Ошибка удаления {eid}: {ex}")
                    else:
                        chat_parts.append("Укажи ID события для удаления.")

                elif action == "chat":
                    chat_parts.append(parsed.get("message", ""))

            if created:
                lines = [f"✅ Создано ({len(created)}):"]
                lines += [f"• {c}" for c in created]
                chat_parts.append("\n".join(lines))

            reply = "\n\n".join(p for p in chat_parts if p)
            # Replace raw AI response in history with actual execution result
            history.append({"role": "assistant", "content": reply or response})
            if reply:
                await update.message.reply_text(reply)

        except Exception as ex:
            logger.exception("AI processing error")
            await update.message.reply_text(f"❌ Ошибка AI: {ex}")

    @staticmethod
    def _parse_actions(response: str) -> list[dict]:
        results = []
        # Extract JSON objects from code blocks
        for block in re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL):
            try:
                results.append(json.loads(block))
            except json.JSONDecodeError:
                pass
        if results:
            return results
        # Extract standalone JSON objects (one per line or separated by whitespace)
        for match in re.finditer(r'\{[^{}]*\}', response):
            try:
                results.append(json.loads(match.group()))
            except json.JSONDecodeError:
                pass
        return results

    async def run(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        logger.info(f"Starting {self.pod_name} with {self.ai.provider_name}/{self.ai.model}")

        await self.health.start()
        logger.info(f"Health server on :5000")

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
