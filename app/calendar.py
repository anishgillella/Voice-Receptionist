"""Google Calendar helper functions."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import get_settings


def _get_service():
    settings = get_settings()
    creds = Credentials.from_authorized_user_info(
        {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }
    )
    return build("calendar", "v3", credentials=creds)


def list_upcoming_events(max_results: int = 5) -> List[Dict[str, Any]]:
    service = _get_service()
    now = datetime.utcnow().isoformat() + "Z"
    events_result = (
        service.events()
        .list(
            calendarId=get_settings().google_calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def create_event(summary: str, start_iso: str, end_iso: str, description: str = "") -> Dict[str, Any]:
    service = _get_service()
    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_iso,
            "timeZone": get_settings().default_timezone,
        },
        "end": {
            "dateTime": end_iso,
            "timeZone": get_settings().default_timezone,
        },
    }
    return (
        service.events()
        .insert(calendarId=get_settings().google_calendar_id, body=event_body)
        .execute()
    )


def update_event(event_id: str, **fields: Any) -> Dict[str, Any]:
    service = _get_service()
    event = service.events().get(calendarId=get_settings().google_calendar_id, eventId=event_id).execute()
    event.update(fields)
    return (
        service.events()
        .update(calendarId=get_settings().google_calendar_id, eventId=event_id, body=event)
        .execute()
    )


def delete_event(event_id: str) -> None:
    service = _get_service()
    try:
        service.events().delete(calendarId=get_settings().google_calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        if exc.resp.status == 404:
            return
        raise


