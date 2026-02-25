#!/usr/bin/env python3
"""SkyProject entry point - PM AI plans, IrgatAI builds, both evolve."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from skyproject.core.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="SkyProject - Self-evolving AI development system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py init                       # Bootstrap: detect, install, index
  python run.py init /path/to/project      # Bootstrap for a target project
  python run.py                            # Run continuous evolution loop
  python run.py --cycles 5                 # Run exactly 5 cycles
  python run.py --interval 60              # 60 seconds between cycles
  python run.py --no-self-improve          # Disable self-improvement
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Bootstrap and initialize SkyProject")
    init_parser.add_argument(
        "target", nargs="?", default=None,
        help="Target project directory (default: SkyProject itself)",
    )

    parser.add_argument(
        "--cycles", type=int, default=0,
        help="Number of cycles to run (0 = infinite)",
    )
    parser.add_argument(
        "--interval", type=int, default=None,
        help="Seconds between cycles (overrides env)",
    )
    parser.add_argument(
        "--no-self-improve", action="store_true",
        help="Disable self-improvement",
    )

    args = parser.parse_args()

    if args.command == "init":
        _run_init(args.target)
        return

    if args.interval is not None:
        from skyproject.core.config import Config
        Config.CYCLE_INTERVAL = args.interval

    if args.no_self_improve:
        from skyproject.core.config import Config
        Config.AUTO_IMPROVE = False

    orchestrator = Orchestrator()

    if args.cycles > 0:
        asyncio.run(_run_n_cycles(orchestrator, args.cycles))
    else:
        asyncio.run(orchestrator.run())


def _run_init(target_dir: str | None) -> None:
    """Run the bootstrap/init process."""
    from skyproject.core.bootstrap import Bootstrap

    bootstrap = Bootstrap(target_dir=target_dir)
    profile = bootstrap.run()

    from rich.console import Console
    console = Console()
    console.print(f"\n[bold green]Ready to go![/bold green]")
    console.print(f"[dim]Run 'python run.py' to start the evolution loop.[/dim]")


async def _run_n_cycles(orchestrator: Orchestrator, n: int):
    """Run exactly N cycles then stop."""
    from rich.console import Console
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
            from skyproject.core.config import Config
            await asyncio.sleep(Config.CYCLE_INTERVAL)

    console.print(f"\n[bold green]Completed {n} cycles.[/bold green]")


if __name__ == "__main__":
    main()
