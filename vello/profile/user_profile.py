import json
import datetime
from pathlib import Path

PROFILE_PATH = Path.home() / ".vello" / "profile.json"


class UserProfile:
    """
    Persistent Digital Twin — everything Vello knows about the user.
    Stored as a JSON file at ~/.vello/profile.json.
    Grows over time as Vello learns more from conversations.
    """

    def __init__(self, path: Path = PROFILE_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return self._default()

    def _default(self) -> dict:
        return {
            "name":   None,
            "email":  None,
            "career": {
                "role":      None,
                "interests": [],
                "skills":    [],
            },
            "goals":       [],
            "preferences": {
                "voice_speed":     "normal",
                "response_style":  "concise",
                "language":        "en",
            },
            "habits": [],
            "routine": {
                "wake_time":  None,
                "sleep_time": None,
                "work_hours": None,
            },
            "created": datetime.datetime.now().isoformat(),
            "updated": datetime.datetime.now().isoformat(),
        }

    def save(self):
        self._data["updated"] = datetime.datetime.now().isoformat()
        self.path.write_text(json.dumps(self._data, indent=2))

    # ── Basic identity ─────────────────────────────────────────────

    @property
    def name(self) -> str | None:
        return self._data.get("name")

    @name.setter
    def name(self, value: str):
        self._data["name"] = value
        self.save()

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    # ── Career & skills ───────────────────────────────────────────

    def set_role(self, role: str):
        self._data["career"]["role"] = role
        self.save()

    def add_skill(self, skill: str):
        skills = self._data["career"]["skills"]
        if skill.lower() not in [s.lower() for s in skills]:
            skills.append(skill)
            self.save()

    def add_interest(self, interest: str):
        interests = self._data["career"]["interests"]
        if interest.lower() not in [i.lower() for i in interests]:
            interests.append(interest)
            self.save()

    # ── Goals ─────────────────────────────────────────────────────

    def add_goal(self, title: str, description: str = "",
                 skills_needed: list = None) -> dict:
        goal = {
            "id":            len(self._data["goals"]) + 1,
            "title":         title,
            "description":   description,
            "skills_needed": skills_needed or [],
            "progress":      0,
            "status":        "active",
            "created":       datetime.datetime.now().isoformat(),
            "milestones":    [],
        }
        self._data["goals"].append(goal)
        self.save()
        return goal

    def get_active_goals(self) -> list:
        return [g for g in self._data["goals"] if g.get("status") == "active"]

    def get_all_goals(self) -> list:
        return self._data["goals"]

    def update_goal_progress(self, goal_id: int, progress: int) -> bool:
        for g in self._data["goals"]:
            if g["id"] == goal_id:
                g["progress"] = min(100, max(0, progress))
                if progress >= 100:
                    g["status"] = "completed"
                self.save()
                return True
        return False

    def complete_goal(self, goal_id: int) -> bool:
        return self.update_goal_progress(goal_id, 100)

    # ── Habits ────────────────────────────────────────────────────

    def learn_habit(self, pattern: str, frequency: str = "daily"):
        """Record or reinforce a recurring behavioral pattern."""
        habits = self._data["habits"]
        for h in habits:
            if h["pattern"].lower() == pattern.lower():
                h["count"] = h.get("count", 0) + 1
                h["last_seen"] = datetime.datetime.now().isoformat()
                self.save()
                return
        habits.append({
            "pattern":    pattern,
            "frequency":  frequency,
            "count":      1,
            "first_seen": datetime.datetime.now().isoformat(),
            "last_seen":  datetime.datetime.now().isoformat(),
        })
        self.save()

    # ── Routine ───────────────────────────────────────────────────

    def set_routine(self, key: str, value: str):
        self._data["routine"][key] = value
        self.save()

    # ── Context summary for GPT ───────────────────────────────────

    def to_summary(self) -> str:
        """One-paragraph summary injected into GPT system prompts."""
        parts = []
        if self._data.get("name"):
            parts.append(f"User's name is {self._data['name']}")
        role = self._data["career"].get("role")
        if role:
            parts.append(f"works as {role}")
        skills = self._data["career"].get("skills", [])
        if skills:
            parts.append(f"skills include {', '.join(skills[:6])}")
        interests = self._data["career"].get("interests", [])
        if interests:
            parts.append(f"interests: {', '.join(interests[:4])}")
        goals = self.get_active_goals()
        if goals:
            goal_titles = [g["title"] for g in goals[:3]]
            parts.append(f"active goals: {'; '.join(goal_titles)}")
        return ". ".join(parts).capitalize() + "." if parts else ""

    def to_spoken_summary(self) -> str:
        """Vello speaks this when user asks 'what do you know about me'."""
        lines = []
        if self._data.get("name"):
            lines.append(f"Your name is {self._data['name']}.")
        role = self._data["career"].get("role")
        if role:
            lines.append(f"You work as {role}.")
        skills = self._data["career"].get("skills", [])
        if skills:
            lines.append(f"I know you have skills in {', '.join(skills[:5])}.")
        goals = self.get_active_goals()
        if goals:
            lines.append(
                f"You have {len(goals)} active goal(s): "
                + ", ".join(g["title"] for g in goals[:3]) + "."
            )
        habits = self._data.get("habits", [])
        if habits:
            top = sorted(habits, key=lambda h: h.get("count", 0), reverse=True)
            lines.append(f"I've noticed you often {top[0]['pattern']}.")
        if not lines:
            return ("I don't know much about you yet. "
                    "Tell me your name, what you do, or what you want to achieve.")
        return " ".join(lines)
