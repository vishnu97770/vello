from openai import OpenAI
import os


class AIBrain:

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are Vello, a helpful AI assistant running on Ubuntu Linux. "
                    "Keep your answers short and clear since they will be spoken aloud."
                )
            }
        ]

    def ask(self, query):
        self.messages.append({"role": "user", "content": query})

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.messages
            )
            reply = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        except Exception as e:
            error_msg = str(e)

            if "quota" in error_msg or "429" in error_msg:
                return (
                    "My AI brain is currently unavailable because "
                    "the API quota is exceeded. But I can still "
                    "handle your system commands."
                )

            if "invalid_api_key" in error_msg or "401" in error_msg:
                return "My API key is invalid. Please check your dot env file."

            print("AI Brain error:", error_msg)
            return "Sorry, I could not process that request right now."

    def reset_memory(self):
        """Clear conversation history but keep system prompt."""
        self.messages = [self.messages[0]]