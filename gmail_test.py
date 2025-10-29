from __future__ import print_function
import os.path
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json first.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def gmail_authenticate():
    """Authenticate and return the Gmail API service"""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If no valid creds, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save creds for next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def send_message(service, to, subject, message_text):
    """Create and send an email message"""
    try:
        message = EmailMessage()
        message.set_content(message_text)
        message["To"] = to
        message["From"] = "me"  # "me" represents the authenticated user
        message["Subject"] = subject

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        # Send it
        sent_message = (
            service.users().messages().send(userId="me", body=create_message).execute()
        )
        print(f"✅ Email sent! Message Id: {sent_message['id']}")
        return sent_message

    except HttpError as error:
        print(f"❌ An error occurred: {error}")
        return None

if __name__ == "__main__":
    service = gmail_authenticate()

    # Test values (replace recipient with a real email)
    recipient = "someone@example.com"
    subject = "✅ Gmail API Test"
    body = "Hello! This is a test email sent from the Gmail API."

    send_message(service, recipient, subject, body)
