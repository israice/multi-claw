import json
import os
from datetime import datetime, timedelta

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """Google Calendar API wrapper (synchronous, wrap calls with asyncio.to_thread)."""

    def __init__(self):
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self.calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

        if creds_json:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
            self.service = build("calendar", "v3", credentials=creds)
        else:
            self.service = None

    def _check(self):
        if not self.service:
            raise RuntimeError("Google Calendar not configured (missing GOOGLE_SERVICE_ACCOUNT_JSON)")

    def list_events(self, start_date: str, end_date: str) -> list[dict]:
        """List events between start_date and end_date (YYYY-MM-DD)."""
        self._check()
        time_min = f"{start_date}T00:00:00Z"
        time_max = f"{end_date}T23:59:59Z"

        result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

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
            })
        return events

    def create_event(self, title: str, date: str, start_time: str, end_time: str, description: str = "") -> dict:
        """Create a calendar event."""
        self._check()
        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": "UTC"},
            "end": {"dateTime": f"{date}T{end_time}:00", "timeZone": "UTC"},
        }
        created = self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        return {"id": created["id"], "title": title, "link": created.get("htmlLink", "")}

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
