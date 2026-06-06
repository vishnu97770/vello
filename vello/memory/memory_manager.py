from .memory_store import MemoryStore


class Memory:
    """A single retrieved memory record."""
    __slots__ = ("id", "type", "content", "context", "importance", "timestamp")

    def __init__(self, row):
        (self.id, self.type, self.content,
         self.context, self.importance, self.timestamp) = row

    def __repr__(self):
        return f"Memory({self.type}: {self.content[:60]})"


class MemoryManager:
    """
    High-level memory API used across all Vello modules.

    Memory types
    ------------
    episodic    — events and conversations that happened
    semantic    — facts the user told Vello about themselves / the world
    procedural  — recurring routines and learned habits
    knowledge   — research answers, documents, notes
    relationship — information about people the user mentions
    """

    def __init__(self):
        self.store = MemoryStore()

    # ── Write ─────────────────────────────────────────────────────

    def remember(self, type_: str, content: str, context: str = None,
                 importance: float = 0.5) -> int:
        """Persist a memory and return its database id."""
        return self.store.insert(type_, content, context, importance)

    # ── Read ──────────────────────────────────────────────────────

    def recall(self, query: str, type_: str = None, limit: int = 5) -> list[Memory]:
        """Search memories by keyword; touch access counters."""
        rows = self.store.search(query, type_, limit)
        memories = [Memory(r) for r in rows]
        for m in memories:
            self.store.touch(m.id)
        return memories

    def recent(self, type_: str = None, limit: int = 5) -> list[Memory]:
        """Return the most recent memories."""
        return [Memory(r) for r in self.store.recent(type_, limit)]

    # ── Delete ────────────────────────────────────────────────────

    def forget(self, memory_id: int):
        self.store.delete(memory_id)

    # ── Context builder for GPT prompts ──────────────────────────

    def build_context_summary(self, query: str, limit: int = 5) -> str:
        """
        Build a short memory-context block to prepend to GPT system prompts.
        Returns empty string when no relevant memories exist.
        """
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""
        lines = ["[Vello Memory]"]
        for m in memories:
            date = m.timestamp[:10]
            lines.append(f"- [{m.type}] {date}: {m.content}")
        return "\n".join(lines)

    def spoken_recall(self, query: str) -> str:
        """Return a spoken-friendly summary of recalled memories."""
        memories = self.recall(query, limit=4)
        if not memories:
            return f"I don't have any memory about {query}."
        lines = [f"Here's what I remember about {query}:"]
        for m in memories:
            date = m.timestamp[:10]
            lines.append(f"On {date} — {m.content}.")
        return " ".join(lines)
