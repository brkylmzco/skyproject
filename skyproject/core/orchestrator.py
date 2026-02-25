from __future__ import annotations

import asyncio
import signal
import time
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skyproject.core.code_index import CodeIndex
from skyproject.core.communication import MessageBus
from skyproject.core.config import Config
from skyproject.core.task_store import TaskStore
from skyproject.irgat_ai.irgat_agent import IrgatAIAgent
from skyproject.pm_ai.pm_agent import PMAIAgent
from skyproject.shared.models import SystemState
from skyproject.core.self_improvement import SelfImprovementFeedbackLoop

console = Console()


class Orchestrator:
    """The main loop that coordinates PM AI and IrgatAI."""

    def __init__(self):
        self.bus = MessageBus()
        self.task_store = TaskStore()
        self.code_index = CodeIndex()
        self.pm = PMAIAgent(self.bus, self.task_store, code_index=self.code_index)
        self.irgat = IrgatAIAgent(self.bus, self.task_store, code_index=self.code_index)
        self.self_improvement = SelfImprovementFeedbackLoop(self.task_store, self.bus)
        self.state = SystemState()
        self._running = False
        self._start_time = 0.0

    async def run(self) -> None:
        """Main run loop."""
        self._running = True
        self._start_time = time.time()

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown)

        self._print_banner()

        console.print("[dim]Ensuring codebase is indexed...[/dim]")
        self.code_index.ensure_indexed()
        console.print(f"[green]Index ready: {self.code_index.store.count} chunks[/green]\n")

        while self._running:
            try:
                await self._run_cycle()
                self.state.cycle_count += 1
                self.state.last_cycle_at = datetime.now()
                self.state.uptime_seconds = time.time() - self._start_time

                if self.state.cycle_count % 5 == 0:
                    await self._print_status()

                if self.state.cycle_count % Config.SELF_IMPROVE_EVERY_N_CYCLES == 0:
                    await self.self_improvement.review_and_propose_improvements()
                    await self.self_improvement.track_and_refine_improvement_proposals()
                    self.code_index.index_all()

                console.print(
                    f"\n[dim]Sleeping {Config.CYCLE_INTERVAL}s before next cycle...[/dim]"
                )
                await asyncio.sleep(Config.CYCLE_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[bold red]Cycle error: {e}[/bold red]")
                await asyncio.sleep(5)

        console.print("\n[bold]SkyProject shutting down gracefully.[/bold]")

    async def run_single_cycle(self) -> dict[str, Any]:
        """Run a single cycle (useful for testing)."""
        return await self._run_cycle()

    async def _run_cycle(self) -> dict[str, Any]:
        """Execute one full cycle: PM plans -> Irgat executes -> PM reviews."""
        cycle_num = self.state.cycle_count + 1

        console.print(
            Panel(
                f"[bold]Cycle #{cycle_num}[/bold]  |  "
                f"Uptime: {time.time() - self._start_time:.0f}s  |  "
                f"Tasks completed: {self.state.total_tasks_completed}  |  "
                f"Improvements: {self.state.total_improvements}  |  "
                f"Index: {self.code_index.store.count} chunks",
                title="[bold cyan]SkyProject[/bold cyan]",
                border_style="cyan",
            )
        )

        pm_result = await self.pm.run_cycle()
        irgat_result = await self.irgat.run_cycle()

        completed = await self.task_store.get_completed()
        self.state.total_tasks_completed = len(completed)

        for action in pm_result.get("actions", []) + irgat_result.get("actions", []):
            if action.get("type") == "self_improve":
                self.state.total_improvements += 1

        return {"pm": pm_result, "irgat": irgat_result}

    async def _print_status(self) -> None:
        counts = await self.task_store.count_by_status()

        table = Table(title="Task Status", border_style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")

        for status, count in counts.items():
            color = {
                "pending": "yellow",
                "in_progress": "blue",
                "in_review": "magenta",
                "completed": "green",
                "failed": "red",
                "cancelled": "dim",
            }.get(status, "white")
            table.add_row(f"[{color}]{status}[/{color}]", str(count))

        console.print(table)

    def _print_banner(self) -> None:
        banner = """
[bold cyan]
 ███████╗██╗  ██╗██╗   ██╗██████╗ ██████╗  ██████╗      ██╗███████╗ ██████╗████████╗
 ██╔════╝██║ ██╔╝╚██╗ ██╔╝██╔══██╗██╔══██╗██╔═══██╗     ██║██╔════╝██╔════╝╚══██╔══╝
 ███████╗█████╔╝  ╚████╔╝ ██████╔╝██████╔╝██║   ██║     ██║█████╗  ██║        ██║
 ╚════██║██╔═██╗   ╚██╔╝  ██╔═══╝ ██╔══██╗██║   ██║██   ██║██╔══╝  ██║        ██║
 ███████║██║  ██╗   ██║   ██║     ██║  ██║╚██████╔╝╚█████╔╝███████╗╚██████╗   ██║
 ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝ ╚═════╝  ╚════╝ ╚══════╝ ╚═════╝   ╚═╝
[/bold cyan]
[bold white]  PM AI plans. IrgatAI builds. Both evolve. Continuously.[/bold white]
[dim]  Vector DB: cost-optimized context retrieval[/dim]
[dim]  Press Ctrl+C to stop gracefully.[/dim]
"""
        console.print(banner)

    def _shutdown(self) -> None:
        console.print("\n[bold yellow]Shutdown signal received...[/bold yellow]")
        self._running = False
