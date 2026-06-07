"""
AIBrain — Grok (xAI) with personality enforcement, memory context, and
optional streaming output for low-latency spoken responses.

Why Grok instead of OpenAI:
  xAI's Grok API is OpenAI SDK-compatible (same library, different base_url).
  Grok-3-mini is fast, cheap, and well-suited to short voice responses.
  Get a free API key at: https://console.x.ai
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    _openai_available = False

from vello.personality import build_system_prompt, clean_response

# xAI Grok endpoint — drop-in compatible with the OpenAI SDK
_XAI_BASE_URL = "https://api.x.ai/v1"
_DEFAULT_MODEL = "grok-3-mini"    # fast, cheap — ideal for voice


class AIBrain:

    _KEY_MISSING_MSG = (
        "AI features are disabled. Add XAI_API_KEY to your .env file "
        "to enable them. Get a free key at console.x.ai. "
        "I can still handle all your system commands."
    )

    def __init__(self, memory=None, profile=None):
        self.memory  = memory
        self.profile = profile
        api_key      = os.getenv("XAI_API_KEY", "").strip()

        if not _openai_available:
            self.client  = None
            self.enabled = False
            print("[AIBrain] openai package not installed — AI disabled.")
        elif not api_key:
            self.client  = None
            self.enabled = False
            print("[AIBrain] No XAI_API_KEY in .env — AI fallback disabled.")
            print("[AIBrain] Get a free key at https://console.x.ai")
            print("[AIBrain] Core voice commands still work fully offline.")
        else:
            self.client  = OpenAI(api_key=api_key, base_url=_XAI_BASE_URL)
            self.enabled = True
            print(f"[AIBrain] Grok ({_DEFAULT_MODEL}) ready via xAI API.")

    # ── System prompt ──────────────────────────────────────────────────────────

    def _system_message(self, query: str = "") -> dict:
        name    = getattr(self.profile, "name", "") or "" if self.profile else ""
        profile = self.profile.to_summary() if self.profile else ""
        memory  = (self.memory.build_context_summary(query, limit=4)
                   if self.memory and query else "")
        content = build_system_prompt(
            user_name      = name,
            profile_summary= profile,
            memory_context = memory,
        )
        return {"role": "system", "content": content}

    # ── Public API ─────────────────────────────────────────────────────────────

    def ask(self, query: str) -> str:
        """Single-turn ask. Returns complete response string."""
        if not self.enabled:
            return self._KEY_MISSING_MSG
        return self.ask_with_context([
            self._system_message(query),
            {"role": "user", "content": query},
        ])

    def ask_with_context(self, messages: list) -> str:
        """Multi-turn ask with conversation history. Returns complete string."""
        if not self.enabled:
            return self._KEY_MISSING_MSG
        if not messages:
            return "I didn't get a question."

        # Replace system message with personality-enforced version
        user_query = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            ""
        )
        enriched_system = self._system_message(user_query)
        if messages and messages[0].get("role") == "system":
            messages = [enriched_system] + messages[1:]
        else:
            messages = [enriched_system] + messages

        try:
            response = self.client.chat.completions.create(
                model=_DEFAULT_MODEL,
                messages=messages,
                max_tokens=300,       # keep spoken responses concise
                temperature=0.7,
            )
            answer = response.choices[0].message.content or ""
            answer = clean_response(answer.strip())

            if self.memory and user_query:
                self.memory.remember(
                    "episodic",
                    f"User: {user_query[:120]} | Vello: {answer[:120]}",
                    context=user_query,
                    importance=0.4,
                )
            return answer

        except Exception as e:
            return self._handle_error(e)

    def ask_streaming(self, query: str):
        """
        Generator that yields text chunks as GPT streams tokens.
        Use with speaker.speak_streaming() for low-latency output.

        Why streaming: with a full response wait, the user hears nothing for
        1-5 seconds. Streaming lets TTS start on the first sentence while
        GPT generates the rest — cuts perceived latency by 60-80%.
        """
        if not self.enabled:
            yield self._KEY_MISSING_MSG
            return

        messages = [
            self._system_message(query),
            {"role": "user", "content": query},
        ]

        try:
            stream = self.client.chat.completions.create(
                model=_DEFAULT_MODEL,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                stream=True,
            )
            full_response = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_response += delta
                    yield delta

            # Store complete response in memory
            if self.memory and full_response:
                cleaned = clean_response(full_response.strip())
                self.memory.remember(
                    "episodic",
                    f"User: {query[:120]} | Vello: {cleaned[:120]}",
                    context=query,
                    importance=0.4,
                )
        except Exception as e:
            yield self._handle_error(e)

    def reset_memory(self):
        pass  # Memory managed by VelloContext + MemoryManager

    # ── Error handling ─────────────────────────────────────────────────────────

    def _handle_error(self, error: Exception) -> str:
        err = str(error)
        if "quota" in err or "429" in err:
            return ("My API quota is exceeded. "
                    "I can still handle your system commands.")
        if "invalid_api_key" in err or "401" in err:
            return "My API key is invalid. Check your dot-env file."
        logger.warning("AIBrain error: %s", err)
        return "I couldn't process that right now. Try again."
