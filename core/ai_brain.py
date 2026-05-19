from openai import OpenAI
import os


class AIBrain:

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._system_msg = {
            "role": "system",
            "content": (
                "You are Vello, a helpful AI assistant running on Ubuntu Linux. "
                "Keep your answers short and clear since they will be spoken aloud."
            ),
        }

    def ask(self, query: str) -> str:
        """Single-turn ask (legacy compatibility)."""
        return self.ask_with_context([
            self._system_msg,
            {"role": "user", "content": query},
        ])

    def ask_with_context(self, messages: list) -> str:
        """Multi-turn ask — messages already include system prompt and history."""
        # Ensure system prompt is present
        if not messages or messages[0].get("role") != "system":
            messages = [self._system_msg] + messages
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            return response.choices[0].message.content

        except Exception as e:
            err = str(e)
            if "quota" in err or "429" in err:
                return (
                    "My AI brain is currently unavailable because "
                    "the API quota is exceeded. I can still handle "
                    "your system commands."
                )
            if "invalid_api_key" in err or "401" in err:
                return "My API key is invalid. Please check your dot env file."
            print("AI Brain error:", err)
            return "Sorry, I could not process that request right now."

    def reset_memory(self):
        pass  # Memory is now managed by VelloContext
