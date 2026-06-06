from openai import OpenAI
import os


class AIBrain:
    """
    GPT-4o-mini fallback brain.
    Now memory-aware and profile-aware — injects long-term context into
    every system prompt so answers feel personal and continuous.
    """

    BASE_SYSTEM = (
        "You are Vello, a helpful AI assistant running on Ubuntu Linux. "
        "Keep your answers short and clear since they will be spoken aloud. "
        "Be conversational and natural — like a trusted personal assistant."
    )

    def __init__(self, memory=None, profile=None):
        self.client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.memory  = memory
        self.profile = profile

    # ── System prompt builder ─────────────────────────────────────

    def _build_system(self, query: str = "") -> dict:
        parts = [self.BASE_SYSTEM]

        if self.profile:
            summary = self.profile.to_summary()
            if summary:
                parts.append(f"\nUser context: {summary}")

        if self.memory and query:
            mem_ctx = self.memory.build_context_summary(query, limit=4)
            if mem_ctx:
                parts.append(f"\n{mem_ctx}")

        return {"role": "system", "content": "\n".join(parts)}

    # ── Public API ────────────────────────────────────────────────

    def ask(self, query: str) -> str:
        """Single-turn ask with memory + profile context."""
        return self.ask_with_context([
            self._build_system(query),
            {"role": "user", "content": query},
        ])

    def ask_with_context(self, messages: list) -> str:
        """
        Multi-turn ask — messages include history.
        Enriches the system message with memory + profile context
        when the first message is the system prompt.
        """
        if not messages:
            return "I didn't get a question."

        # Inject enriched system prompt
        user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_query = m.get("content", "")
                break

        if messages[0].get("role") == "system":
            messages = [self._build_system(user_query)] + messages[1:]
        else:
            messages = [self._build_system(user_query)] + messages

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
            answer = response.choices[0].message.content

            # Store the exchange in episodic memory
            if self.memory and user_query:
                self.memory.remember(
                    "episodic",
                    f"User asked: {user_query[:150]} | Vello answered: {answer[:150]}",
                    context=user_query,
                    importance=0.4,
                )

            return answer

        except Exception as e:
            err = str(e)
            if "quota" in err or "429" in err:
                return (
                    "My AI brain is currently unavailable because "
                    "the API quota is exceeded. I can still handle "
                    "your system commands."
                )
            if "invalid_api_key" in err or "401" in err:
                return "My API key is invalid. Please check your dot-env file."
            print("AI Brain error:", err)
            return "Sorry, I could not process that request right now."

    def reset_memory(self):
        pass  # Memory is managed by VelloContext + MemoryManager
