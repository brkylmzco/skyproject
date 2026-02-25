"""SkyProject CLI — entry point for `skyproject` command."""
from __future__ import annotations

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="skyproject",
        description="SkyProject — Self-evolving AI development system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  skyproject init                       # Bootstrap: detect, install, index
  skyproject init /path/to/project      # Bootstrap targeting another project
  skyproject run                        # Continuous evolution loop
  skyproject run --cycles 5             # Run exactly 5 cycles
  skyproject run --no-self-improve      # Disable self-improvement
  skyproject web                        # Start Web UI on :8080
  skyproject web --port 9000            # Custom port
  skyproject status                     # Show system status
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # init
    init_p = subparsers.add_parser("init", help="Bootstrap and initialize SkyProject")
    init_p.add_argument("target", nargs="?", default=None, help="Target project directory")

    # run
    run_p = subparsers.add_parser("run", help="Start the evolution loop")
    run_p.add_argument("--cycles", type=int, default=0, help="Number of cycles (0 = infinite)")
    run_p.add_argument("--interval", type=int, default=None, help="Seconds between cycles")
    run_p.add_argument("--no-self-improve", action="store_true", help="Disable self-improvement")
    run_p.add_argument("--web", action="store_true", help="Also start Web UI in background")
    run_p.add_argument("--web-port", type=int, default=None, help="Web UI port (default 8080)")

    # web
    web_p = subparsers.add_parser("web", help="Start the Web UI")
    web_p.add_argument("--port", type=int, default=None, help="Port (default 8080)")
    web_p.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")

    # status
    subparsers.add_parser("status", help="Show current system status")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        _cmd_init(args.target)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "web":
        _cmd_web(args)
    elif args.command == "status":
        _cmd_status()


def _cmd_init(target_dir: str | None) -> None:
    from skyproject.core.bootstrap import Bootstrap
    from rich.console import Console

    bootstrap = Bootstrap(target_dir=target_dir)
    bootstrap.run()

    Console().print("\n[bold green]Ready! Run 'skyproject run' to start.[/bold green]")


def _cmd_run(args) -> None:
    import os
    import threading
    from skyproject.core.config import Config
    from skyproject.core.orchestrator import Orchestrator
    from skyproject.telegram.bot import SkyTelegramBot

    if args.interval is not None:
        Config.CYCLE_INTERVAL = args.interval
    if args.no_self_improve:
        Config.AUTO_IMPROVE = False

    orchestrator = Orchestrator()
    orchestrator.telegram_bot = SkyTelegramBot(orchestrator)

    if getattr(args, "web", False) or os.getenv("SKY_WEB_ENABLED", "").lower() == "true":
        port = getattr(args, "web_port", None) or int(os.getenv("SKY_WEB_PORT", "8080"))
        _start_web_background(orchestrator, port)

    if args.cycles > 0:
        asyncio.run(_run_n_cycles(orchestrator, args.cycles))
    else:
        asyncio.run(orchestrator.run())


def _cmd_web(args) -> None:
    import os
    import uvicorn
    from skyproject.web.app import create_app
    from skyproject.core.orchestrator import Orchestrator

    port = args.port or int(os.getenv("SKY_WEB_PORT", "8080"))
    host = args.host

    orchestrator = Orchestrator()
    app = create_app(orchestrator=orchestrator)

    print(f"Starting SkyProject Web UI on http://{host}:{port}")
    print("Login with admin / admin (you will be asked to change the password)")
    uvicorn.run(app, host=host, port=port, log_level="info")


def _start_web_background(orchestrator, port: int = 8080) -> None:
    """Start the web UI in a background thread."""
    import threading
    import uvicorn
    from skyproject.web.app import create_app

    app = create_app(orchestrator=orchestrator)

    def _run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"Web UI started in background on http://0.0.0.0:{port}")


def _cmd_status() -> None:
    import json
    from pathlib import Path
    from rich.console import Console
    from rich.table import Table

    console = Console()
    data_dir = Path(__file__).parent.parent / "data"

    config_file = data_dir / "project_config.json"
    if config_file.exists():
        profile = json.loads(config_file.read_text())
        console.print(f"[bold]Project:[/bold] {profile.get('project_dir', 'unknown')}")
        console.print(f"[bold]Language:[/bold] {profile.get('primary_language', 'unknown')}")
        console.print(f"[bold]Frameworks:[/bold] {', '.join(profile.get('frameworks', [])) or 'none'}")
        console.print(f"[bold]Source files:[/bold] {profile.get('file_count', 0)}")
    else:
        console.print("[yellow]Not initialized. Run 'skyproject init' first.[/yellow]")
        return

    tasks_dir = data_dir / "tasks"
    if tasks_dir.exists():
        task_files = list(tasks_dir.glob("*.json"))
        console.print(f"[bold]Tasks:[/bold] {len(task_files)}")

    vector_dir = data_dir / "vector_db"
    if vector_dir.exists():
        console.print("[bold]Vector DB:[/bold] [green]active[/green]")


async def _run_n_cycles(orchestrator, n: int):
    from rich.console import Console
    from skyproject.core.config import Config

    console = Console()
    orchestrator._print_banner()

    for i in range(n):
        result = await orchestrator.run_single_cycle()
        orchestrator.state.cycle_count += 1

        pm_actions = len(result.get("pm", {}).get("actions", []))
        irgat_actions = len(result.get("irgat", {}).get("actions", []))
        console.print(
            f"\n[dim]Cycle {i + 1}/{n} complete. "
            f"PM: {pm_actions} actions, Irgat: {irgat_actions} actions[/dim]"
        )

        if i < n - 1:
            await asyncio.sleep(Config.CYCLE_INTERVAL)

    console.print(f"\n[bold green]Completed {n} cycles.[/bold green]")
