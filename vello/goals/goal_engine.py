import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class GoalEngine:
    """
    Decomposes user goals into structured, actionable plans.
    Integrates with UserProfile for persistence.
    """

    def __init__(self, profile=None, memory=None):
        self.profile = profile
        self.memory  = memory
        self._client = None

    def _get_client(self) -> OpenAI | None:
        if not self._client:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                self._client = OpenAI(api_key=key)
        return self._client

    # ── Set a new goal ────────────────────────────────────────────

    def set_goal(self, raw_text: str) -> str:
        """Parse a user's stated goal, persist it, return spoken confirmation."""
        if not self.profile:
            return "Profile system is unavailable."

        client = self._get_client()
        title, description, skills_needed = raw_text, "", []

        if client:
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": (
                            "Extract the goal from the user's statement. "
                            "Reply with valid JSON only — no markdown:\n"
                            '{"title": "...", "description": "...", '
                            '"skills_needed": ["..."]}'
                        )},
                        {"role": "user", "content": raw_text},
                    ],
                    max_tokens=200,
                )
                data = json.loads(resp.choices[0].message.content)
                title         = data.get("title", raw_text)
                description   = data.get("description", "")
                skills_needed = data.get("skills_needed", [])
            except Exception as e:
                logger.warning("GoalEngine.set_goal GPT parse error: %s", e)

        goal = self.profile.add_goal(title, description, skills_needed)

        # Store in episodic memory
        if self.memory:
            self.memory.remember(
                "episodic",
                f"User set a new goal: {title}",
                context=description,
                importance=0.9,
            )

        active_count = len(self.profile.get_active_goals())
        return (
            f"Goal saved: {title}. "
            f"I'll help you work toward this every day. "
            f"You now have {active_count} active goal(s). "
            f"Say 'plan for {title}' and I'll create an action plan."
        )

    # ── Generate an action plan ────────────────────────────────────

    def get_action_plan(self, goal_title: str) -> str:
        """Ask GPT to build a spoken step-by-step plan for a goal."""
        client = self._get_client()
        if not client:
            return "AI is unavailable. Please check your API key."

        profile_ctx = self.profile.to_summary() if self.profile else ""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You are Vello, an AI life coach. "
                        "Create a concise 5-step action plan that will be read aloud. "
                        "Use natural spoken language, no bullet symbols. "
                        "Number each step. Be practical and specific. "
                        f"User context: {profile_ctx}"
                    )},
                    {"role": "user", "content":
                        f"Create an action plan for: {goal_title}"},
                ],
                max_tokens=350,
            )
            plan = resp.choices[0].message.content

            if self.memory:
                self.memory.remember(
                    "knowledge",
                    f"Action plan for '{goal_title}': {plan[:300]}",
                    context=goal_title,
                    importance=0.8,
                )

            return plan
        except Exception as e:
            logger.error("GoalEngine.get_action_plan error: %s", e)
            return "Could not generate a plan right now."

    # ── List goals ────────────────────────────────────────────────

    def list_goals(self) -> str:
        if not self.profile:
            return "Profile system is unavailable."
        goals = self.profile.get_active_goals()
        if not goals:
            return (
                "You have no active goals. "
                "Tell me something you want to achieve and I'll track it for you."
            )
        parts = [f"You have {len(goals)} active goal(s)."]
        for i, g in enumerate(goals, 1):
            pct = g.get("progress", 0)
            parts.append(f"Goal {i}: {g['title']}, {pct} percent complete.")
        return " ".join(parts)

    # ── Update progress ───────────────────────────────────────────

    def update_progress(self, goal_id: int, progress: int) -> str:
        if not self.profile:
            return "Profile system is unavailable."
        success = self.profile.update_goal_progress(goal_id, progress)
        if not success:
            return f"I couldn't find goal number {goal_id}."
        if progress >= 100:
            return f"Congratulations! Goal {goal_id} is complete!"
        return f"Goal {goal_id} updated to {progress} percent complete."
