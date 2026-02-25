"""PM AI Agent - the unified Project Manager interface."""
from __future__ import annotations

import logging
from typing import Any, Optional

from rich.console import Console

from skyproject.core.communication import MessageBus
from skyproject.core.config import Config
from skyproject.core.task_store import TaskStore
from skyproject.pm_ai.self_improve import PMSelfImprover
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import (
    Message,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
    ReviewResult,
)

console = Console()
logger = logging.getLogger(__name__)


class PMAIAgent:
    """The PM AI agent that plans, prioritizes, and reviews."""

    def __init__(self, bus: MessageBus, task_store: TaskStore, code_index=None):
        self.llm = LLMClient()
        self.bus = bus
        self.task_store = task_store
        self.code_index = code_index
        self.self_improver = PMSelfImprover(self.llm, code_index=code_index)
        self.cycle_count = 0

    async def run_cycle(self) -> dict[str, Any]:
        """Run one PM AI cycle: analyze -> plan -> assign -> review."""
        self.cycle_count += 1
        cycle_result = {"cycle": self.cycle_count, "actions": []}

        console.print(f"\n[bold blue]━━━ PM AI Cycle #{self.cycle_count} ━━━[/bold blue]")

        messages = await self.bus.receive_all("pm")
        for msg in messages:
            action = await self._handle_message(msg)
            if action:
                cycle_result["actions"].append(action)

        pending = await self.task_store.get_pending()
        if not pending:
            new_tasks = await self._plan_tasks()
            for task in new_tasks:
                await self.task_store.save(task)
                await self.bus.send(Message(
                    sender="pm",
                    receiver="irgat",
                    msg_type="task_assign",
                    payload=task.model_dump(mode="json"),
                ))
                console.print(f"  [blue]Assigned:[/blue] {task.title}")
                cycle_result["actions"].append({"type": "assign", "task": task.title})

        if self.cycle_count % Config.SELF_IMPROVE_EVERY_N_CYCLES == 0 and Config.AUTO_IMPROVE:
            console.print("[blue]PM AI self-improvement analysis...[/blue]")
            proposals = await self.self_improver.analyze_self()
            for proposal in proposals[:1]:
                console.print(f"  [magenta]Self-improve:[/magenta] {proposal.title}")
                await self.self_improver.apply_improvement(proposal)
                cycle_result["actions"].append({"type": "self_improve", "title": proposal.title})

        return cycle_result

    async def _plan_tasks(self) -> list[Task]:
        """Use LLM + vector search to analyze codebase and create tasks."""
        try:
            context = ""
            if self.code_index:
                self.code_index.ensure_indexed()
                for module in ("pm_ai", "irgat_ai", "core", "shared"):
                    summary = self.code_index.get_module_summary(module)
                    if summary:
                        context += f"\n## Module: {module}\n{summary}\n"

                improvement_ctx = self.code_index.get_context_for_task(
                    "areas needing improvement, bugs, missing features, code quality issues",
                    max_tokens=2000,
                )
                context += f"\n## Relevant code for analysis:\n{improvement_ctx}\n"

            prompt = f"""Analyze the current codebase and create 1-3 actionable tasks.

Codebase overview:
{context}

For each task, specify:
- title: concise task name
- description: what needs to be done and why
- task_type: feature / bug_fix / refactor / test / documentation
- priority: critical / high / medium / low
- target_module: pm_ai / irgat_ai / core / shared

Respond with JSON:
{{
    "tasks": [
        {{
            "title": "task title",
            "description": "detailed description",
            "task_type": "refactor",
            "priority": "medium",
            "target_module": "core"
        }}
    ]
}}"""

            result = await self.llm.generate_json(Config.PM_SYSTEM_PROMPT, prompt)
            tasks = []
            for t in result.get("tasks", []):
                tasks.append(Task(
                    title=t["title"],
                    description=t["description"],
                    task_type=TaskType(t.get("task_type", "feature")),
                    priority=TaskPriority(t.get("priority", "medium")),
                    target_module=t.get("target_module", ""),
                    assigned_to="irgat",
                ))
            logger.info("PM planned %d tasks", len(tasks))
            return tasks
        except Exception as e:
            logger.error("PM planning failed: %s", e)
            return []

    async def _handle_message(self, msg: Message) -> Optional[dict[str, Any]]:
        if msg.msg_type == "review_request":
            task_id = msg.payload.get("task_id")
            task = await self.task_store.load(task_id)
            if not task:
                return None

            review = await self._review_task(task)

            if review.approved:
                await self.task_store.update_status(task_id, TaskStatus.COMPLETED)
                console.print(f"[green]Approved:[/green] {task.title} (score: {review.quality_score:.1f})")
            else:
                console.print(f"[yellow]Needs revision:[/yellow] {task.title}")

            await self.bus.send(Message(
                sender="pm",
                receiver="irgat",
                msg_type="review_result",
                payload={
                    "task_id": task_id,
                    "approved": review.approved,
                    "feedback": review.feedback,
                    "suggestions": review.suggestions,
                },
            ))
            return {"type": "review", "task": task.title, "approved": review.approved}

        return None

    async def _review_task(self, task: Task) -> ReviewResult:
        """Review a completed task using vector search for context."""
        try:
            context = ""
            if self.code_index and task.code_changes:
                for change in task.code_changes:
                    related = self.code_index.get_context_for_task(
                        f"code related to {change.file_path}",
                        max_tokens=500,
                    )
                    context += f"\n{related}\n"

            changes_text = "\n".join(
                f"File: {c.file_path}\nChange: {c.change_type}\nContent:\n{c.new_content[:500]}"
                for c in task.code_changes
            ) if task.code_changes else "No code changes recorded"

            prompt = f"""Review this completed task:

Task: {task.title}
Description: {task.description}

Code changes:
{changes_text}

Related codebase context:
{context}

Evaluate: code quality, correctness, test coverage, documentation.

Respond with JSON:
{{
    "approved": true/false,
    "feedback": "detailed feedback",
    "quality_score": 0-10,
    "suggestions": ["suggestion1", "suggestion2"]
}}"""

            result = await self.llm.generate_json(Config.PM_SYSTEM_PROMPT, prompt)
            return ReviewResult(
                task_id=task.id,
                approved=result.get("approved", False),
                feedback=result.get("feedback", ""),
                quality_score=result.get("quality_score", 0.0),
                suggestions=result.get("suggestions", []),
            )
        except Exception as e:
            logger.error("Review failed for task %s: %s", task.id, e)
            return ReviewResult(task_id=task.id, approved=False, feedback=f"Review error: {e}")
