import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'gmail_token.json'


def get_gmail_service():
    """Authenticate and return Gmail service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email and return its message ID and thread ID."""
    service = get_gmail_service()
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()
    return {'id': sent['id'], 'threadId': sent['threadId']}


def _extract_text_from_payload(payload: dict) -> str:
    """Recursively search a message payload for the first text/plain part."""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    for part in payload.get('parts', []):
        text = _extract_text_from_payload(part)
        if text:
            return text
    return ''


def get_replies(thread_id: str) -> list:
    """Get all messages in a thread."""
    service = get_gmail_service()
    thread = service.users().threads().get(
        userId='me', id=thread_id
    ).execute()
    messages = []
    for msg in thread.get('messages', [])[1:]:  # skip first (our sent email)
        body = _extract_text_from_payload(msg['payload'])
        if body:
            messages.append({
                'id': msg['id'],
                'body': body,
                'snippet': msg.get('snippet', '')
            })
    return messages


def check_for_reply(thread_id: str, known_message_ids: list) -> dict | None:
    """Check if there's a new reply in the thread."""
    replies = get_replies(thread_id)
    for reply in replies:
        if reply['id'] not in known_message_ids:
            return reply
    return None
