import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

AGENT_DESCRIPTIONS = {
    "research": (
        "research, explanations, learning, 'what is', 'how does', "
        "information gathering, analysis, comparisons"
    ),
    "coding": (
        "code help, debugging, explaining code, programming questions, "
        "software engineering, algorithms, errors in code"
    ),
    "goals": (
        "setting goals, tracking progress, career planning, "
        "'I want to become', 'my goal is', action plans"
    ),
    "memory": (
        "remembering past conversations, 'what did I tell you', "
        "'do you remember', recalling information"
    ),
    "profile": (
        "user identity questions, 'what do you know about me', "
        "updating name/role/skills, 'my name is', 'I work as'"
    ),
    "general": (
        "system commands, greetings, casual conversation, "
        "anything not covered by other agents"
    ),
}


class ExecutiveAgent:
    """
    Coordinator agent. Routes queries to the right specialist agent.
    Falls back to 'general' when routing is ambiguous or AI is unavailable.
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

    def route(self, query: str) -> str:
        """Return the agent type best suited for the query."""
        client = self._get_client()
        if not client:
            return "general"

        agent_list = "\n".join(
            f'  "{k}": {v}' for k, v in AGENT_DESCRIPTIONS.items()
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        f"Route the user query to the correct agent.\n"
                        f"Agents:\n{agent_list}\n"
                        f"Reply with ONE agent name only. No explanation."
                    )},
                    {"role": "user", "content": query},
                ],
                max_tokens=10,
            )
            agent = resp.choices[0].message.content.strip().lower()
            if agent in AGENT_DESCRIPTIONS:
                logger.debug("ExecutiveAgent routed '%s' → %s", query[:40], agent)
                return agent
        except Exception as e:
            logger.warning("ExecutiveAgent routing error: %s", e)

        return "general"
