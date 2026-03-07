import json
import os
from datetime import datetime, timedelta

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Google Calendar API wrapper (synchronous, wrap calls with asyncio.to_thread)."""

    def __init__(self):
        self.calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        self.timezone = os.environ.get("CALENDAR_TIMEZONE", "UTC")
        creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

        if creds_file and os.path.isfile(creds_file):
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
            self.service = build("calendar", "v3", credentials=creds)
        elif creds_json:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            self.service = build("calendar", "v3", credentials=creds)
        else:
            self.service = None

    def _check(self):
        if not self.service:
            raise RuntimeError("Google Calendar not configured (missing GOOGLE_SERVICE_ACCOUNT_JSON)")

    @staticmethod
    def _to_rfc3339(date: str, time_str: str) -> str:
        """Normalize date + time into RFC3339 format: YYYY-MM-DDTHH:MM:SS"""
        t = time_str.strip()
        # Handle HH:MM:SS, HH:MM, or other formats
        parts = t.split(":")
        h = parts[0] if len(parts) > 0 else "00"
        m = parts[1] if len(parts) > 1 else "00"
        s = parts[2] if len(parts) > 2 else "00"
        return f"{date}T{h}:{m}:{s}"

    def list_events(self, start_date: str, end_date: str, query: str = "") -> list[dict]:
        """List events between start_date and end_date (YYYY-MM-DD)."""
        self._check()
        time_min = f"{start_date}T00:00:00Z"
        time_max = f"{end_date}T23:59:59Z"

        kwargs = {
            "calendarId": self.calendar_id,
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if query:
            kwargs["q"] = query

        result = self.service.events().list(**kwargs).execute()

        events = []
        for item in result.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date", ""))
            end = item["end"].get("dateTime", item["end"].get("date", ""))
            events.append({
                "id": item["id"],
                "title": item.get("summary", "(no title)"),
                "start": start,
                "end": end,
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "attendees": [a.get("email", "") for a in item.get("attendees", [])],
                "recurrence": item.get("recurrence", []),
                "all_day": "date" in item["start"],
            })
        return events

    def get_event(self, event_id: str) -> dict:
        """Get a single event by ID."""
        self._check()
        item = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
        start = item["start"].get("dateTime", item["start"].get("date", ""))
        end = item["end"].get("dateTime", item["end"].get("date", ""))
        return {
            "id": item["id"],
            "title": item.get("summary", "(no title)"),
            "start": start,
            "end": end,
            "description": item.get("description", ""),
            "location": item.get("location", ""),
            "attendees": [a.get("email", "") for a in item.get("attendees", [])],
            "recurrence": item.get("recurrence", []),
            "all_day": "date" in item["start"],
        }

    def create_event(self, title: str, date: str, start_time: str = "", end_time: str = "",
                     description: str = "", location: str = "", attendees: list[str] | None = None,
                     recurrence: list[str] | None = None, reminders_minutes: list[int] | None = None,
                     all_day: bool = False) -> dict:
        """Create a calendar event. Supports timed events, all-day events, recurrence, attendees, reminders."""
        self._check()

        event_body = {
            "summary": title,
            "description": description,
        }

        if location:
            event_body["location"] = location

        if all_day or (not start_time and not end_time):
            event_body["start"] = {"date": date}
            # All-day events: end date is exclusive, so next day
            end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            event_body["end"] = {"date": end_date}
        else:
            event_body["start"] = {"dateTime": self._to_rfc3339(date, start_time), "timeZone": self.timezone}
            event_body["end"] = {"dateTime": self._to_rfc3339(date, end_time), "timeZone": self.timezone}

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        if recurrence:
            event_body["recurrence"] = recurrence

        if reminders_minutes:
            event_body["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in reminders_minutes],
            }

        created = self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        return {"id": created["id"], "title": title, "link": created.get("htmlLink", "")}

    def update_event(self, event_id: str, title: str = "", description: str = "",
                     date: str = "", start_time: str = "", end_time: str = "",
                     location: str = "", attendees: list[str] | None = None,
                     recurrence: list[str] | None = None, reminders_minutes: list[int] | None = None,
                     all_day: bool | None = None) -> dict:
        """Update an existing event. Only provided fields are changed."""
        self._check()
        item = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()

        if title:
            item["summary"] = title
        if description:
            item["description"] = description
        if location:
            item["location"] = location

        if all_day:
            d = date or item["start"].get("date", item["start"].get("dateTime", "")[:10])
            item["start"] = {"date": d}
            end_d = (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            item["end"] = {"date": end_d}
        elif date or start_time or end_time:
            cur_date = item["start"].get("dateTime", item["start"].get("date", ""))[:10]
            cur_start = item["start"].get("dateTime", "T08:00:00")[11:16]
            cur_end = item["end"].get("dateTime", "T09:00")[11:16]
            d = date or cur_date
            st = start_time or cur_start
            et = end_time or cur_end
            item["start"] = {"dateTime": self._to_rfc3339(d, st), "timeZone": self.timezone}
            item["end"] = {"dateTime": self._to_rfc3339(d, et), "timeZone": self.timezone}

        if attendees is not None:
            item["attendees"] = [{"email": email} for email in attendees]

        if recurrence is not None:
            item["recurrence"] = recurrence

        if reminders_minutes is not None:
            item["reminders"] = {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in reminders_minutes],
            }

        updated = self.service.events().update(
            calendarId=self.calendar_id, eventId=event_id, body=item
        ).execute()
        return {"id": updated["id"], "title": updated.get("summary", "")}

    def quick_add(self, text: str) -> dict:
        """Create event from natural language text (Google's quickAdd)."""
        self._check()
        created = self.service.events().quickAdd(calendarId=self.calendar_id, text=text).execute()
        start = created["start"].get("dateTime", created["start"].get("date", ""))
        return {
            "id": created["id"],
            "title": created.get("summary", text),
            "start": start,
            "link": created.get("htmlLink", ""),
        }

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        self._check()
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
        return True

    def find_free_slots(self, date: str, slot_minutes: int = 60) -> list[dict]:
        """Find free time slots on a given date."""
        self._check()
        events = self.list_events(date, date)

        day_start = datetime.strptime(f"{date} 08:00", "%Y-%m-%d %H:%M")
        day_end = datetime.strptime(f"{date} 20:00", "%Y-%m-%d %H:%M")

        busy = []
        for e in events:
            s = e["start"]
            en = e["end"]
            if "T" in s:
                s_dt = datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
                e_dt = datetime.fromisoformat(en.replace("Z", "+00:00")).replace(tzinfo=None)
                busy.append((s_dt, e_dt))

        busy.sort(key=lambda x: x[0])

        free = []
        current = day_start
        for b_start, b_end in busy:
            if current + timedelta(minutes=slot_minutes) <= b_start:
                free.append({
                    "start": current.strftime("%H:%M"),
                    "end": b_start.strftime("%H:%M"),
                })
            current = max(current, b_end)

        if current + timedelta(minutes=slot_minutes) <= day_end:
            free.append({
                "start": current.strftime("%H:%M"),
                "end": day_end.strftime("%H:%M"),
            })

        return free
