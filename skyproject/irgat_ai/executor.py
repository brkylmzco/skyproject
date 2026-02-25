"""Task execution coordinator for IrgatAI."""
from __future__ import annotations

import logging
from datetime import datetime

from rich.console import Console

from skyproject.irgat_ai.coder import Coder
from skyproject.irgat_ai.tester import Tester
from skyproject.shared.file_ops import write_file
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import CodeChange, Task, TaskStatus

logger = logging.getLogger(__name__)
console = Console()


class Executor:
    """Coordinates code generation, validation, and application."""

    def __init__(self, llm: LLMClient, code_index=None):
        self.coder = Coder(llm, code_index=code_index)
        self.tester = Tester()

    async def execute_task(self, task: Task) -> Task:
        """Execute a task: generate code -> validate -> apply."""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        try:
            console.print(f"[yellow]Executing:[/yellow] {task.title}")

            console.print("  Generating code...")
            changes = await self.coder.implement(task)
            console.print(f"  Generated {len(changes)} file change(s)")

            console.print("  Validating...")
            valid = await self.tester.validate_changes(changes)

            if valid:
                console.print("  Applying changes...")
                for change in changes:
                    await write_file(change.file_path, change.new_content)

                task.code_changes = changes
                task.status = TaskStatus.IN_REVIEW
                task.completed_at = datetime.now()
                console.print("  [green]Implementation complete, requesting review[/green]")
            else:
                task.status = TaskStatus.FAILED
                task.review_notes = "Validation failed"
                console.print("  [red]Validation failed[/red]")

        except Exception as e:
            logger.error("Task execution failed for '%s': %s", task.title, e, exc_info=True)
            task.status = TaskStatus.FAILED
            task.review_notes = f"Execution error: {e}"
            console.print(f"  [red]Error: {e}[/red]")

        return task

    async def execute_with_feedback(
        self, task: Task, feedback: str, suggestions: list[str]
    ) -> Task:
        """Re-execute a task based on review feedback."""
        task.status = TaskStatus.IN_PROGRESS

        try:
            console.print(f"[yellow]Revising:[/yellow] {task.title}")

            changes = await self.coder.improve_from_feedback(task, feedback, suggestions)
            console.print(f"  Generated {len(changes)} revised change(s)")

            valid = await self.tester.validate_changes(changes)

            if valid:
                for change in changes:
                    await write_file(change.file_path, change.new_content)

                task.code_changes = changes
                task.status = TaskStatus.IN_REVIEW
                task.completed_at = datetime.now()
                console.print("  [green]Revision complete, requesting re-review[/green]")
            else:
                task.status = TaskStatus.FAILED
                task.review_notes = "Validation failed after revision"
                console.print("  [red]Revision validation failed[/red]")

        except Exception as e:
            logger.error("Revision failed for '%s': %s", task.title, e, exc_info=True)
            task.status = TaskStatus.FAILED
            task.review_notes = f"Revision error: {e}"

        return task
