import os

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


load_dotenv()


CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    raise RuntimeError("Missing Google OAuth environment variables. Ensure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN are set.")

creds = Credentials.from_authorized_user_info(
    {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "scopes": ["https://www.googleapis.com/auth/calendar"],
    }
)

service = build("calendar", "v3", credentials=creds)

events_result = (
    service.events()
    .list(calendarId=CALENDAR_ID, maxResults=10, singleEvents=True, orderBy="startTime")
    .execute()
)

events = events_result.get("items", [])

if not events:
    print("No upcoming events found.")

for event in events:
    summary = event.get("summary", "(no title)")
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
    print(summary, start)