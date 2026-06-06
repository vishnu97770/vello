import os
import webbrowser
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class ResearchAgent:
    """
    Handles research, explanations, and information gathering.
    Enriches GPT answers with long-term memory context.
    Stores answers back to knowledge memory for future retrieval.
    """

    def __init__(self, memory=None, profile=None):
        self.memory  = memory
        self.profile = profile
        self._client = None

    def _get_client(self) -> OpenAI | None:
        if not self._client:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                self._client = OpenAI(api_key=key)
        return self._client

    def research(self, query: str, save: bool = True) -> str:
        """Research a topic and return a spoken-friendly answer."""
        client = self._get_client()
        if not client:
            webbrowser.open(
                "https://www.google.com/search?q=" + query.replace(" ", "+")
            )
            return f"I've opened a search for '{query}' in your browser."

        memory_ctx  = self.memory.build_context_summary(query) if self.memory else ""
        profile_ctx = self.profile.to_summary()                if self.profile else ""

        system_msg = (
            "You are Vello, an intelligent research assistant. "
            "Give clear, conversational answers — they will be spoken aloud. "
            "Aim for 3-5 sentences unless the user asks for more detail. "
            "Be accurate, helpful, and natural."
        )
        if profile_ctx:
            system_msg += f"\n\nUser context: {profile_ctx}"
        if memory_ctx:
            system_msg += f"\n\n{memory_ctx}"

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": query},
                ],
                max_tokens=400,
            )
            answer = resp.choices[0].message.content

            if save and self.memory:
                self.memory.remember(
                    "knowledge",
                    f"Q: {query} | A: {answer[:250]}",
                    context=query,
                    importance=0.6,
                )

            return answer

        except Exception as e:
            logger.error("ResearchAgent.research error: %s", e)
            return "I ran into a problem while researching that. Please try again."

    def explain(self, topic: str) -> str:
        return self.research(f"Explain {topic} simply")

    def compare(self, a: str, b: str) -> str:
        return self.research(f"Compare {a} and {b} briefly")

    def summarize(self, text: str) -> str:
        return self.research(f"Summarize this in 3 sentences: {text}")
