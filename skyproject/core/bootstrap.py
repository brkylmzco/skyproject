"""Bootstrap layer - auto-detects environment, installs deps, configures, and starts the system."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


class ProjectDetector:
    """Detects the target project's language, framework, and structure."""

    LANG_SIGNATURES = {
        "python": {
            "files": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "setup.cfg"],
            "extensions": [".py"],
        },
        "javascript": {
            "files": ["package.json"],
            "extensions": [".js", ".jsx"],
        },
        "typescript": {
            "files": ["tsconfig.json", "package.json"],
            "extensions": [".ts", ".tsx"],
        },
        "go": {
            "files": ["go.mod", "go.sum"],
            "extensions": [".go"],
        },
        "rust": {
            "files": ["Cargo.toml"],
            "extensions": [".rs"],
        },
        "java": {
            "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "extensions": [".java"],
        },
    }

    FRAMEWORK_SIGNATURES = {
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py"],
        "fastapi": ["main.py"],
        "react": ["src/App.js", "src/App.tsx", "src/index.js", "src/index.tsx"],
        "nextjs": ["next.config.js", "next.config.mjs", "next.config.ts"],
        "express": ["server.js", "app.js"],
    }

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def detect(self) -> dict:
        """Return a full project profile."""
        languages = self._detect_languages()
        frameworks = self._detect_frameworks()
        structure = self._detect_structure()

        return {
            "project_dir": str(self.project_dir),
            "languages": languages,
            "primary_language": languages[0] if languages else "unknown",
            "frameworks": frameworks,
            "structure": structure,
            "has_git": (self.project_dir / ".git").exists(),
            "has_tests": any(
                (self.project_dir / d).exists()
                for d in ["tests", "test", "__tests__", "spec"]
            ),
            "has_ci": any(
                (self.project_dir / f).exists()
                for f in [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci"]
            ),
            "file_count": self._count_source_files(languages),
        }

    def _detect_languages(self) -> list[str]:
        detected = []
        for lang, sigs in self.LANG_SIGNATURES.items():
            for sig_file in sigs["files"]:
                if (self.project_dir / sig_file).exists():
                    if lang not in detected:
                        detected.append(lang)
                    break

        if not detected:
            ext_counts: dict[str, int] = {}
            for f in self.project_dir.rglob("*"):
                if f.is_file() and not any(p.startswith(".") for p in f.parts):
                    ext_counts[f.suffix] = ext_counts.get(f.suffix, 0) + 1

            for lang, sigs in self.LANG_SIGNATURES.items():
                for ext in sigs["extensions"]:
                    if ext_counts.get(ext, 0) > 3:
                        if lang not in detected:
                            detected.append(lang)
                        break

        return detected

    def _detect_frameworks(self) -> list[str]:
        detected = []
        for fw, markers in self.FRAMEWORK_SIGNATURES.items():
            for marker in markers:
                if (self.project_dir / marker).exists():
                    detected.append(fw)
                    break

        pkg_json = self.project_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                fw_packages = {
                    "react": "react",
                    "vue": "vue",
                    "angular": "@angular/core",
                    "svelte": "svelte",
                    "express": "express",
                    "nextjs": "next",
                    "nuxt": "nuxt",
                }
                for fw_name, pkg_name in fw_packages.items():
                    if pkg_name in all_deps and fw_name not in detected:
                        detected.append(fw_name)
            except (json.JSONDecodeError, OSError):
                pass

        return detected

    def _detect_structure(self) -> dict:
        top_dirs = [d.name for d in self.project_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        top_files = [f.name for f in self.project_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        return {"directories": sorted(top_dirs), "files": sorted(top_files)}

    def _count_source_files(self, languages: list[str]) -> int:
        extensions = set()
        for lang in languages:
            for ext in self.LANG_SIGNATURES.get(lang, {}).get("extensions", []):
                extensions.add(ext)

        if not extensions:
            extensions = {".py", ".js", ".ts", ".go", ".rs", ".java"}

        count = 0
        for f in self.project_dir.rglob("*"):
            if f.is_file() and f.suffix in extensions:
                if not any(p.startswith(".") for p in f.parts) and "__pycache__" not in str(f):
                    count += 1
        return count


class Bootstrap:
    """Auto-setup and configuration for SkyProject."""

    def __init__(self, target_dir: Optional[str] = None):
        self.sky_root = Path(__file__).parent.parent.parent
        self.target_dir = Path(target_dir) if target_dir else self.sky_root
        self.data_dir = self.sky_root / "data"
        self.config_file = self.data_dir / "project_config.json"

    def run(self) -> dict:
        """Full bootstrap sequence."""
        console.print(Panel("[bold cyan]SkyProject Bootstrap[/bold cyan]", border_style="cyan"))

        self._ensure_directories()
        self._check_python_version()
        self._install_dependencies()
        self._setup_env()

        project_profile = self._detect_project()
        self._save_config(project_profile)
        self._index_codebase(project_profile)

        console.print("\n[bold green]Bootstrap complete![/bold green]")
        return project_profile

    def _ensure_directories(self) -> None:
        console.print("[dim]Creating data directories...[/dim]")
        for d in ["tasks", "logs", "improvements", "vector_db"]:
            (self.data_dir / d).mkdir(parents=True, exist_ok=True)

    def _check_python_version(self) -> None:
        v = sys.version_info
        if v < (3, 10):
            console.print(f"[bold red]Python 3.10+ required, found {v.major}.{v.minor}[/bold red]")
            sys.exit(1)
        console.print(f"[green]Python {v.major}.{v.minor}.{v.micro}[/green]")

    def _install_dependencies(self) -> None:
        req_file = self.sky_root / "requirements.txt"
        if not req_file.exists():
            logger.warning("requirements.txt not found, skipping dependency install")
            return

        console.print("[dim]Installing dependencies...[/dim]")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                check=True,
                capture_output=True,
                text=True,
            )
            console.print("[green]Dependencies installed[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Dependency install warning: {e.stderr[:200]}[/yellow]")

    def _setup_env(self) -> None:
        env_file = self.sky_root / ".env"
        if env_file.exists():
            console.print("[green].env found[/green]")
            return

        env_example = self.sky_root / ".env.example"
        if env_example.exists():
            shutil.copy(env_example, env_file)
            console.print("[yellow].env created from .env.example — please set your API keys[/yellow]")
            return

        default_env = (
            "# SkyProject configuration\n"
            "LLM_PROVIDER=openai\n"
            "LLM_MODEL=gpt-4o\n"
            "OPENAI_API_KEY=your-key-here\n"
            "\n"
            "# Optional\n"
            "# ANTHROPIC_API_KEY=your-key-here\n"
            "# SKY_AUTO_IMPROVE=true\n"
            "# SKY_CYCLE_INTERVAL=30\n"
            "# SKY_LOG_LEVEL=INFO\n"
        )
        env_file.write_text(default_env)
        console.print("[yellow].env created — please set OPENAI_API_KEY[/yellow]")

    def _detect_project(self) -> dict:
        console.print(f"[dim]Detecting project at {self.target_dir}...[/dim]")
        detector = ProjectDetector(self.target_dir)
        profile = detector.detect()

        console.print(f"  Language: [cyan]{profile['primary_language']}[/cyan]")
        console.print(f"  Frameworks: [cyan]{', '.join(profile['frameworks']) or 'none'}[/cyan]")
        console.print(f"  Source files: [cyan]{profile['file_count']}[/cyan]")
        console.print(f"  Git: [cyan]{'yes' if profile['has_git'] else 'no'}[/cyan]")
        console.print(f"  Tests: [cyan]{'yes' if profile['has_tests'] else 'no'}[/cyan]")

        return profile

    def _index_codebase(self, profile: dict) -> None:
        console.print("[dim]Indexing codebase into vector DB...[/dim]")
        try:
            from skyproject.core.code_index import CodeIndex
            index = CodeIndex()

            index.index_all()

            if str(self.target_dir) != str(self.sky_root):
                index.index_directory(str(self.target_dir))

            console.print(f"[green]Indexed {index.store.count} code chunks[/green]")
        except Exception as e:
            console.print(f"[yellow]Indexing warning: {e}[/yellow]")

    def _save_config(self, profile: dict) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(profile, indent=2, default=str))
        console.print("[green]Project config saved[/green]")
