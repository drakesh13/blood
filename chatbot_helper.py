# chatbot_helper.py
from gpt4all import GPT4All
import re

# -----------------------
# GPT4All model setup
# -----------------------
MODEL_PATH = r"C:\Users\madhu\AppData\Local\nomic.ai\GPT4All\gpt4all-falcon-newbpe-q4_0.gguf"
model = GPT4All(MODEL_PATH)

system_prompt = """You are Rakth Sathi Assistant.
You help users with blood donation questions as well as questions about the Rakth Sathi app.
You provide clear, helpful, and friendly guidance.
You answer questions about blood donation, eligibility criteria, donation process, post-donation care.
You also answer questions about Rakth Sathi, such as how it works, registration, blood donor safety, privacy, trustworthiness, and services.
You can answer general questions, chat casually, tell facts, jokes, and provide guidance on daily life topics.
You do not provide medical advice.
Always be friendly and helpful."""

# -----------------------
# Short conversation memory
# -----------------------
MAX_HISTORY = 3  # last N messages to remember
conversation_history_list = []  # stores tuples (user, bot)

# -----------------------
# Blood donation rules
# -----------------------
def blood_compatible_info(target_bg):
    compat = {
        "O-": ["O-"],
        "O+": ["O-", "O+"],
        "A-": ["O-", "A-"],
        "A+": ["O-", "O+", "A-", "A+"],
        "B-": ["O-", "B-"],
        "B+": ["O-", "O+", "B-", "B+"],
        "AB-": ["O-", "A-", "B-", "AB-"],
        "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
    }
    return compat.get(target_bg.upper(), [])

def common_blood_questions(user_message):
    msg = user_message.lower()
    # Periods
    if "period" in msg or "menstrual" in msg:
        return "Yes, you can donate blood during your menstrual cycle as long as you are feeling well. Check with your local blood donation center for specifics."
    # Cold
    if "cold" in msg:
        return "It is usually recommended to wait until your cold symptoms have cleared before donating blood."
    # Fever
    if "fever" in msg:
        return "You should not donate blood if you have a fever. Wait until you are fully recovered."
    # Blood group compatibility
    match = re.search(r'([ABO]{1,2}[+-])', user_message.upper())
    if match:
        target_bg = match.group(1)
        donors = blood_compatible_info(target_bg)
        return f"Individuals with the following blood groups can donate to {target_bg}: {', '.join(donors)}"
    return None

# -----------------------
# Rakth Sathi app FAQ rules
# -----------------------
def rakth_sathi_faq(user_message):
    msg = user_message.lower()
    if "trust" in msg or "safe" in msg or "reliable" in msg:
        return ("Rakth Sathi is a trusted platform that connects blood donors with recipients. "
                "All donor information is handled securely and privacy is maintained.")
    if "how to register" in msg or "sign up" in msg:
        return "You can register in Rakth Sathi by filling the signup form in the app with your basic information and blood group."
    if "features" in msg or "services" in msg:
        return "Rakth Sathi allows you to find blood donors nearby, check donor availability, track donations, and get reminders for your next donation."
    if "what is rakth sathi" in msg or "about rakth sathi" in msg:
        return "Rakth Sathi is a platform that connects blood donors with people in need, helping ensure timely blood donations and supporting donor awareness."
    return None

# -----------------------
# Main function
# -----------------------
def get_bot_reply(user_message):
    global conversation_history_list
    try:
        # 1️⃣ Check for blood donation rules
        rule_answer = common_blood_questions(user_message)
        if rule_answer:
            return rule_answer

        # 2️⃣ Check Rakth Sathi FAQ rules
        rakth_answer = rakth_sathi_faq(user_message)
        if rakth_answer:
            return rakth_answer

        # 3️⃣ GPT4All fallback
        prompt_context = ""
        for u, b in conversation_history_list[-MAX_HISTORY:]:
            prompt_context += f"User: {u}\nAssistant: {b}\n"
        prompt_context += f"User: {user_message}\nAssistant:"

        prompt = system_prompt + "\n" + prompt_context

        # Generate GPT4All response
        reply = model.generate(prompt, max_tokens=200)

        # Save to conversation history
        conversation_history_list.append((user_message, reply.strip()))
        return reply.strip()

    except Exception as e:
        print("GPT4All error:", e)
        return "Sorry, I am unable to answer right now."
