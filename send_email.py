import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")

def send_email(to_email: str, recipient_name: str, subject: str, body: str, urgency: str = "Normal"):
    """
    Send an email with recipient details and urgency.
    
    urgency can be: "High", "Normal", "Low"
    """
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        raise RuntimeError("❌ Missing SENDER_EMAIL or SENDER_APP_PASSWORD in environment or .env")

    # Build email
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add urgency header for email clients
    if urgency.lower() == "high":
        msg["X-Priority"] = "1"
        msg["Importance"] = "High"
    elif urgency.lower() == "low":
        msg["X-Priority"] = "5"
        msg["Importance"] = "Low"

    # Personalize body with recipient name + urgency info
    personalized_body = f"""
Hi {recipient_name},

{body}

⚡ Urgency: {urgency}
"""
    msg.attach(MIMEText(personalized_body, "plain"))

    # Send email via Gmail SMTP
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {recipient_name} ({to_email}) with urgency: {urgency}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")

# -----------------------
# Main block
# -----------------------
if __name__ == "__main__":
    # Recipient details
    test_to = os.getenv("TEST_RECIPIENT", "donor@example.com")
    recipient_name = "Donor"
    subject = "Urgent Blood Donation Request"

    # Ask user for urgency level
    urgency_level = input("Enter urgency level (High / Normal / Low): ").strip().capitalize()
    if urgency_level not in ["High", "Normal", "Low"]:
        print("⚠️ Invalid input. Defaulting urgency to 'Normal'.")
        urgency_level = "Normal"

    # Example patient details
    patient_details = {
        "name": "John Doe",
        "age": 42,
        "blood_group": "O+",
        "hospital": "City Hospital, Emergency Ward",
        "contact": "+1-555-123-4567",
        "needed_by": "September 22, 2025"
    }

    # Step 1: Send email WITHOUT phone number
    body_initial = f"""
Patient Name: {patient_details['name']}
Age: {patient_details['age']}
Blood Group: {patient_details['blood_group']}
Hospital: {patient_details['hospital']}
Needed By: {patient_details['needed_by']}

Please come forward if you can donate blood.
"""
    print(f"📧 Sending initial email to {test_to} without contact number ...")
    send_email(test_to, recipient_name, subject, body_initial, urgency=urgency_level)

    # Step 2: If donor accepts, send phone number
    donor_response = input("Did the donor accept the request? (yes/no): ").strip().lower()
    if donor_response == "yes":
        body_with_contact = f"""
Patient Name: {patient_details['name']}
Age: {patient_details['age']}
Blood Group: {patient_details['blood_group']}
Hospital: {patient_details['hospital']}
Needed By: {patient_details['needed_by']}
Contact: {patient_details['contact']}

Thank you for agreeing to donate blood.
"""
        print(f"📧 Sending follow-up email to {test_to} with contact number ...")
        send_email(test_to, recipient_name, subject + " - Contact Info", body_with_contact, urgency=urgency_level)
    else:
        print("ℹ️ Donor did not accept the request. No contact info sent.")
