import os
import base64
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def gmail_authenticate():
    """Authenticate Gmail API using token.json"""
    if not os.path.exists("token.json"):
        raise RuntimeError("❌ Run the Gmail API auth flow first to create token.json")
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

def send_email(service, to, subject, body):
    """Send an email"""
    message = EmailMessage()
    message.set_content(body)
    message["To"] = to
    message["From"] = "me"
    message["Subject"] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}

    service.users().messages().send(userId="me", body=create_message).execute()
    print(f"📧 Email sent to {to} with subject '{subject}'")

def send_consent_request(service, donor_email):
    """Ask donor for consent"""
    body = (
        "Hi Donor,\n\n"
        "Would you be willing to donate blood?\n\n"
        "👉 Please reply with YES to confirm, or NO to decline."
    )
    send_email(service, donor_email, "Blood Donation Consent Request", body)

def check_donor_reply(service, donor_email):
    """Check for donor's YES reply"""
    try:
        results = service.users().messages().list(
            userId="me",
            q=f"from:{donor_email} subject:'Blood Donation Consent Request'",
            maxResults=5
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            print("❌ No reply found yet.")
            return False

        for msg in messages:
            txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
            snippet = txt.get("snippet", "").lower()
            if "yes" in snippet:
                print("✅ Donor replied YES!")
                return True

        print("❌ Donor has not replied YES yet.")
        return False

    except HttpError as error:
        print(f"❌ Error checking reply: {error}")
        return False

def send_patient_details(service, donor_email, patient_info):
    """Send patient details once donor agrees"""
    body = f"""
Thank you for agreeing to donate! 🙏
Here are the patient details:

👤 Name: {patient_info['name']}
🎂 Age: {patient_info['age']}
🩸 Blood Group: {patient_info['blood_group']}
🏥 Hospital: {patient_info['hospital']}
📞 Contact: {patient_info['contact']}
"""
    send_email(service, donor_email, "Patient Details for Blood Donation", body)

if __name__ == "__main__":
    service = gmail_authenticate()

    # Donor email (dynamic from env var)
    donor = os.getenv("TEST_RECIPIENT", "donor@example.com")

    # Patient details (dynamic from env vars)
    patient_details = {
        "name": os.getenv("PATIENT_NAME", "Ramesh Kumar"),
        "age": os.getenv("PATIENT_AGE", "52"),
        "blood_group": os.getenv("PATIENT_BLOOD", "B+"),
        "hospital": os.getenv("PATIENT_HOSPITAL", "Apollo Hospital, Hyderabad"),
        "contact": os.getenv("PATIENT_CONTACT", "+91-9876543210"),
    }

    # Step 1: Send consent request
    send_consent_request(service, donor)

    # Step 2: Check donor reply
    if check_donor_reply(service, donor):
        send_patient_details(service, donor, patient_details)
