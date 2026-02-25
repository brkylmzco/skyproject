"""Code generation engine for IrgatAI."""
from __future__ import annotations

import json
import logging
from typing import Any

from skyproject.irgat_ai.exceptions import JSONDecodeError, CoderError
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import CodeChange, Task
from skyproject.core.config import Config

logger = logging.getLogger(__name__)


class Coder:
    """Generates code changes based on task descriptions using LLM."""

    def __init__(self, llm: LLMClient, code_index=None):
        self.llm = llm
        self._code_index = code_index

    async def implement(self, task: Task) -> list[CodeChange]:
        """Generate code changes for a task."""
        try:
            context = ""
            if self._code_index:
                context = self._code_index.get_context_for_task(
                    f"{task.title}: {task.description}",
                    module=task.target_module or None,
                    max_tokens=2000,
                )

            prompt = f"""Implement the following task:

Title: {task.title}
Description: {task.description}
Target module: {task.target_module}

Relevant codebase context:
{context}

Respond with JSON:
{{
    "changes": [
        {{
            "file_path": "path/to/file.py",
            "new_content": "complete file content",
            "change_type": "modify"
        }}
    ]
}}"""

            result = await self.llm.generate_json(Config.IRGAT_SYSTEM_PROMPT, prompt)
            changes = []
            for c in result.get("changes", []):
                changes.append(CodeChange(
                    file_path=c["file_path"],
                    new_content=c["new_content"],
                    change_type=c.get("change_type", "modify"),
                ))
            return changes

        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON response: %s", e, exc_info=True)
            raise JSONDecodeError("Failed to decode JSON response from LLM", e)
        except Exception as e:
            logger.error("Error implementing task: %s", e, exc_info=True)
            raise CoderError("Unexpected error in code implementation", e)

    async def improve_from_feedback(
        self, task: Task, feedback: str, suggestions: list[str]
    ) -> list[CodeChange]:
        """Re-implement a task based on review feedback."""
        try:
            context = ""
            if self._code_index:
                context = self._code_index.get_context_for_task(
                    f"{task.title}: {feedback}",
                    module=task.target_module or None,
                    max_tokens=1500,
                )

            suggestions_text = "\n".join(f"- {s}" for s in suggestions) if suggestions else "None"

            prompt = f"""Revise your implementation based on review feedback:

Task: {task.title}
Description: {task.description}

Feedback: {feedback}
Suggestions:
{suggestions_text}

Relevant context:
{context}

Respond with JSON:
{{
    "changes": [
        {{
            "file_path": "path/to/file.py",
            "new_content": "complete revised file content",
            "change_type": "modify"
        }}
    ]
}}"""

            result = await self.llm.generate_json(Config.IRGAT_SYSTEM_PROMPT, prompt)
            changes = []
            for c in result.get("changes", []):
                changes.append(CodeChange(
                    file_path=c["file_path"],
                    new_content=c["new_content"],
                    change_type=c.get("change_type", "modify"),
                ))
            return changes

        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON response: %s", e, exc_info=True)
            raise JSONDecodeError("Failed to decode JSON response from LLM", e)
        except Exception as e:
            logger.error("Error improving from feedback: %s", e, exc_info=True)
            raise CoderError("Unexpected error in feedback improvement", e)
