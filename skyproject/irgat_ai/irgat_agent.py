"""IrgatAI Agent - the unified IrgatAI interface."""
from __future__ import annotations

from typing import Any, Optional

from rich.console import Console

from skyproject.core.communication import MessageBus
from skyproject.core.config import Config
from skyproject.core.task_store import TaskStore
from skyproject.irgat_ai.executor import Executor
from skyproject.irgat_ai.self_improve import IrgatSelfImprover
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import (
    Message,
    Task,
    TaskStatus,
)

console = Console()


class IrgatAIAgent:
    """The IrgatAI agent that executes tasks and builds features."""

    def __init__(self, bus: MessageBus, task_store: TaskStore, code_index=None):
        self.llm = LLMClient()
        self.bus = bus
        self.task_store = task_store
        self.code_index = code_index
        self.executor = Executor(self.llm)
        self.self_improver = IrgatSelfImprover(self.llm, code_index=code_index)
        self.cycle_count = 0
        self._retry_counts: dict[str, int] = {}

    async def run_cycle(self) -> dict[str, Any]:
        """Run one IrgatAI cycle: receive tasks -> execute -> report."""
        self.cycle_count += 1
        cycle_result = {"cycle": self.cycle_count, "actions": []}

        console.print(f"\n[bold yellow]━━━ IrgatAI Cycle #{self.cycle_count} ━━━[/bold yellow]")

        messages = await self.bus.receive_all("irgat")
        for msg in messages:
            action = await self._handle_message(msg)
            if action:
                cycle_result["actions"].append(action)

        if self.cycle_count % Config.SELF_IMPROVE_EVERY_N_CYCLES == 0 and Config.AUTO_IMPROVE:
            console.print("[yellow]IrgatAI self-improvement analysis...[/yellow]")
            proposals = await self.self_improver.analyze_self()
            for proposal in proposals[:1]:
                console.print(f"  [magenta]Self-improve:[/magenta] {proposal.title}")
                await self.self_improver.apply_improvement(proposal)
                cycle_result["actions"].append({"type": "self_improve", "title": proposal.title})

        return cycle_result

    async def _handle_message(self, msg: Message) -> Optional[dict[str, Any]]:
        if msg.msg_type == "task_assign":
            task = Task(**msg.payload)
            console.print(f"[yellow]Received task:[/yellow] {task.title}")

            result_task = await self.executor.execute_task(task)
            await self.task_store.save(result_task)

            if self.code_index and result_task.code_changes:
                for change in result_task.code_changes:
                    self.code_index.index_file(change.file_path, change.new_content)

            if result_task.status == TaskStatus.IN_REVIEW:
                await self.bus.send(Message(
                    sender="irgat",
                    receiver="pm",
                    msg_type="review_request",
                    payload={"task_id": result_task.id},
                ))
                return {"type": "executed", "task": task.title, "status": "in_review"}
            else:
                await self.bus.send(Message(
                    sender="irgat",
                    receiver="pm",
                    msg_type="status_update",
                    payload={"task_id": result_task.id, "status": result_task.status.value},
                ))
                return {"type": "executed", "task": task.title, "status": "failed"}

        elif msg.msg_type == "review_result":
            task_id = msg.payload.get("task_id")
            approved = msg.payload.get("approved", False)

            if not approved:
                retries = self._retry_counts.get(task_id, 0)
                if retries < Config.MAX_RETRIES:
                    self._retry_counts[task_id] = retries + 1
                    task = await self.task_store.load(task_id)
                    if task:
                        console.print(f"[yellow]Revising (attempt {retries + 1}):[/yellow] {task.title}")
                        result_task = await self.executor.execute_with_feedback(
                            task,
                            msg.payload.get("feedback", ""),
                            msg.payload.get("suggestions", []),
                        )
                        await self.task_store.save(result_task)

                        if result_task.status == TaskStatus.IN_REVIEW:
                            await self.bus.send(Message(
                                sender="irgat",
                                receiver="pm",
                                msg_type="review_request",
                                payload={"task_id": result_task.id},
                            ))
                        return {"type": "revised", "task_id": task_id, "attempt": retries + 1}
                else:
                    console.print(f"[red]Max retries reached for task {task_id}[/red]")
                    await self.task_store.update_status(task_id, TaskStatus.FAILED)
                    return {"type": "max_retries", "task_id": task_id}
            else:
                if task_id in self._retry_counts:
                    del self._retry_counts[task_id]
                console.print(f"[green]Task approved: {task_id}[/green]")
                return {"type": "approved", "task_id": task_id}

        return None
