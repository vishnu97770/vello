import os
import subprocess
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class CodingAgent:
    """
    Handles software engineering questions: code help, debugging, explanations.
    Answers are optimized for being spoken aloud.
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

    def assist(self, task: str) -> str:
        """Answer a coding question in a spoken-friendly way."""
        client = self._get_client()
        if not client:
            return "AI is unavailable. Check your API key in the dot-env file."

        profile_ctx = self.profile.to_summary() if self.profile else ""
        memory_ctx  = self.memory.build_context_summary(task) if self.memory else ""

        system_msg = (
            "You are Vello's coding assistant. "
            "Answers will be read aloud, so avoid raw code blocks — "
            "describe what the code does instead of reading it character by character. "
            "Be practical, direct, and concise. "
            "If the answer requires seeing code, ask the user to show you their screen."
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
                    {"role": "user",   "content": task},
                ],
                max_tokens=400,
            )
            answer = resp.choices[0].message.content

            if self.memory:
                self.memory.remember(
                    "knowledge",
                    f"Coding help: {task[:100]} → {answer[:200]}",
                    context=task,
                    importance=0.5,
                )

            return answer

        except Exception as e:
            logger.error("CodingAgent.assist error: %s", e)
            return "Could not process that coding question right now."

    def open_editor(self, project: str = None) -> str:
        cmd = ["code"]
        if project:
            cmd.append(project)
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            suffix = f" on {project}" if project else ""
            return f"VS Code is ready{suffix}. What are you building?"
        except FileNotFoundError:
            return "VS Code is not installed or not in your PATH."
