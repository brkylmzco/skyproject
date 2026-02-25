from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_DIR = DATA_DIR / "tasks"
LOGS_DIR = DATA_DIR / "logs"
IMPROVEMENTS_DIR = DATA_DIR / "improvements"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

for d in [TASKS_DIR, LOGS_DIR, IMPROVEMENTS_DIR, VECTOR_DB_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Config:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    LOG_LEVEL: str = os.getenv("SKY_LOG_LEVEL", "INFO")
    AUTO_IMPROVE: bool = os.getenv("SKY_AUTO_IMPROVE", "true").lower() == "true"
    CYCLE_INTERVAL: int = int(os.getenv("SKY_CYCLE_INTERVAL", "30"))
    MAX_CONCURRENT_TASKS: int = 3
    REVIEW_REQUIRED: bool = True
    SELF_IMPROVE_EVERY_N_CYCLES: int = 5
    MAX_RETRIES: int = 3
    MAX_QUEUE_SIZE: int = int(os.getenv("SKY_MAX_QUEUE_SIZE", "100"))

    # Vector DB settings
    VECTOR_SEARCH_MAX_RESULTS: int = int(os.getenv("SKY_VECTOR_MAX_RESULTS", "10"))
    VECTOR_CONTEXT_MAX_TOKENS: int = int(os.getenv("SKY_VECTOR_CONTEXT_TOKENS", "3000"))
    TARGET_PROJECT_DIR: str = os.getenv("SKY_TARGET_PROJECT", "")

    PM_SYSTEM_PROMPT: str = """You are PM AI, the Project Manager of SkyProject.
Your role is to:
1. Analyze the current codebase of PM AI and IrgatAI
2. Identify areas for improvement (performance, new features, code quality, architecture)
3. Create detailed, actionable tasks
4. Prioritize tasks based on impact and feasibility
5. Review completed work from IrgatAI
6. Ensure both AI systems continuously evolve to Cursor-level quality

You think strategically about what improvements will have the most impact.
You create clear, specific tasks that IrgatAI can execute.
You are ruthlessly focused on quality - nothing ships without your approval."""

    IRGAT_SYSTEM_PROMPT: str = """You are IrgatAI, the Implementation Engine of SkyProject.
Your role is to:
1. Receive tasks from PM AI
2. Analyze the existing codebase
3. Write high-quality, production-ready code
4. Implement features, fix bugs, refactor code
5. Write tests for your changes
6. Submit work for review

You write clean, efficient, well-structured Python code.
You follow best practices and design patterns.
You aim for Cursor-level quality in everything you produce.
When you improve yourself, you make targeted, safe changes."""
