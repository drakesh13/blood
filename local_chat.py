from gpt4all import GPT4All

MODEL_PATH = r"C:\Users\madhu\AppData\Local\nomic.ai\GPT4All\gpt4all-falcon-newbpe-q4_0.gguf"
model = GPT4All(MODEL_PATH)

system_prompt = """You are Rakth Sathi Assistant.
You help users with blood donation questions.
You provide clear, helpful, and friendly guidance.
You have know blood related.
You have knowledge about blood donation, eligibility criteria, donation process, and post-donation care.
You provide accurate and up-to-date information.
You do not provide medical advice.
You answer for blood  related queries .
You answer questions about how to donate, eligibility, locations, and related services."""

def chat():
    print("Local GPT4All chat (type 'exit' to quit)")
    while True:
        msg = input("You: ")
        if msg.lower() in ("exit","quit"):
            break
        prompt = system_prompt + "\nUser: " + msg + "\nAssistant:"
        reply = model.generate(prompt, max_tokens=200)
        print("Bot:", reply)

if __name__ == "__main__":
    chat()
