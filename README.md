# SkyProject

> **PM AI plans. IrgatAI builds. Both evolve. Continuously.**

SkyProject is a self-evolving AI development system. Drop it into any project and it will analyze, plan, implement, review, and improve — autonomously and continuously.

Two AI agents work as a team:

- **PM AI** — analyzes codebases, creates tasks, prioritizes work, reviews code
- **IrgatAI** — writes production-quality code, executes tasks, builds features

Both agents continuously improve their own source code, creating an ever-accelerating feedback loop.

## Key Features

- **Drop-in deployment** — `skyproject init` auto-detects your project's language, framework, and structure
- **Vector DB powered** — ChromaDB with local embeddings (`all-MiniLM-L6-v2`) for cost-efficient context retrieval. No API calls for embeddings.
- **~80-90% cost reduction** — only relevant code chunks are sent to the LLM, not entire files
- **Self-evolving** — both AI agents analyze and upgrade their own code every N cycles
- **Safety first** — snapshots before every modification, review gates, syntax validation, retry limits
- **Multi-provider** — supports OpenAI and Anthropic
- **Language agnostic detection** — auto-detects Python, JavaScript, TypeScript, Go, Rust, Java projects

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Orchestrator                       │
│           (continuous evolution loop)                 │
├────────────────────┬─────────────────────────────────┤
│                    │                                  │
│   ┌──────────┐     │     ┌──────────────┐            │
│   │  PM AI   │◄────┼────►│   IrgatAI    │            │
│   │          │     │     │              │            │
│   │ Planner  │   Message │ Coder        │            │
│   │ Reviewer │    Bus    │ Executor     │            │
│   │ Priority │     │     │ Tester       │            │
│   │ Improve  │     │     │ Improve      │            │
│   └──────────┘     │     └──────────────┘            │
│                    │                                  │
├────────────────────┴─────────────────────────────────┤
│                   Shared Layer                        │
│  Models · LLM Client · File Ops · Vector Store       │
├──────────────────────────────────────────────────────┤
│                  Code Index                           │
│  ChromaDB · AST Chunker · Semantic Search             │
└──────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: From source

```bash
git clone https://github.com/brkylmzco/skyproject.git
cd skyproject

python3 -m venv venv
source venv/bin/activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env — set your OPENAI_API_KEY

# Initialize & index
skyproject init

# Start evolving
skyproject run
```

### Option 2: Docker

```bash
git clone https://github.com/brkylmzco/skyproject.git
cd skyproject

cp .env.example .env
# Edit .env — set your OPENAI_API_KEY

docker compose up
```

### Option 3: Target another project

```bash
# Point SkyProject at your project
skyproject init /path/to/your/project

# It will auto-detect language, framework, structure
# Then start developing it
skyproject run
```

## Usage

```bash
# Initialize (auto-detect, install deps, index codebase)
skyproject init

# Run continuous evolution loop
skyproject run

# Run exactly 5 cycles
skyproject run --cycles 5

# Custom interval between cycles
skyproject run --interval 60

# Disable self-improvement (for testing)
skyproject run --no-self-improve

# Check system status
skyproject status
```

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `LLM_MODEL` | `gpt-4o` | Model to use |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (if using anthropic) |
| `SKY_AUTO_IMPROVE` | `true` | Enable self-improvement |
| `SKY_CYCLE_INTERVAL` | `30` | Seconds between cycles |
| `SKY_LOG_LEVEL` | `INFO` | Logging level |
| `SKY_VECTOR_MAX_RESULTS` | `10` | Max vector search results per query |
| `SKY_VECTOR_CONTEXT_TOKENS` | `3000` | Max tokens for context retrieval |
| `SKY_TARGET_PROJECT` | — | Path to target project (optional) |

## Project Structure

```
skyproject/
├── run.py                              # Legacy entry point
├── pyproject.toml                      # Package configuration
├── requirements.txt                    # Dependencies
├── Dockerfile                          # Container support
├── docker-compose.yml
├── Makefile                            # Dev shortcuts
├── .env.example                        # Configuration template
│
├── skyproject/
│   ├── cli.py                          # CLI entry point (skyproject command)
│   ├── core/
│   │   ├── orchestrator.py             # Main evolution loop
│   │   ├── communication.py            # PM ↔ Irgat async message bus
│   │   ├── task_store.py               # File-based task persistence
│   │   ├── config.py                   # Central configuration
│   │   ├── bootstrap.py                # Auto-setup & project detection
│   │   ├── code_index.py               # Code index manager
│   │   ├── self_improvement.py         # Feedback loop for self-improvement
│   │   └── improvement_tracker.py      # Improvement tracking
│   │
│   ├── pm_ai/
│   │   ├── pm_agent.py                 # PM AI unified agent
│   │   ├── planner.py                  # Codebase analysis & task creation
│   │   ├── reviewer.py                 # Code review engine
│   │   ├── prioritizer.py              # Task prioritization
│   │   └── self_improve.py             # PM self-improvement (vector-powered)
│   │
│   ├── irgat_ai/
│   │   ├── irgat_agent.py              # IrgatAI unified agent
│   │   ├── coder.py                    # Code generation engine
│   │   ├── executor.py                 # Task execution coordinator
│   │   ├── tester.py                   # Code validation & testing
│   │   ├── self_improve.py             # Irgat self-improvement (vector-powered)
│   │   └── anomaly_detector.py         # Anomaly detection
│   │
│   └── shared/
│       ├── models.py                   # Pydantic data models
│       ├── llm_client.py               # OpenAI/Anthropic client
│       ├── file_ops.py                 # Async file operations
│       ├── vector_store.py             # ChromaDB vector store
│       ├── code_chunker.py             # AST-based code chunker
│       └── prompt_generation.py        # Dynamic prompt generation
│
├── data/                               # Runtime data (gitignored)
│   ├── tasks/                          # Task queue
│   ├── logs/                           # Activity logs
│   ├── improvements/                   # Pre-modification snapshots
│   └── vector_db/                      # ChromaDB persistence
│
└── tests/                              # Test suite
```

## How the Evolution Loop Works

```
Cycle 1:
  PM AI  → Analyzes codebase via vector search
  PM AI  → Creates task: "Add retry logic to executor"
  PM AI  → Assigns task to IrgatAI via MessageBus
  IrgatAI → Receives task, retrieves relevant code from vector DB
  IrgatAI → Implements changes, submits for review
  PM AI  → Reviews: quality 8/10, approved ✓
  Index  → Re-indexes modified files

Cycle 5 (self-improvement):
  PM AI  → Analyzes own code: "Planner needs better context handling"
  PM AI  → Upgrades its own planning logic
  IrgatAI → Analyzes own code: "Tester lacks edge case coverage"
  IrgatAI → Upgrades its own testing engine
  Index  → Full re-index after improvements
```

## Cost Optimization

SkyProject uses a **vector DB** (ChromaDB) with **local embeddings** to minimize LLM API costs:

| Approach | Tokens per cycle | Cost estimate |
|---|---|---|
| Before (full source) | ~100K+ tokens | ~$0.30/cycle |
| After (vector search) | ~3-5K tokens | ~$0.01-0.02/cycle |

Embeddings run locally via `all-MiniLM-L6-v2` — zero API cost for indexing and retrieval.

## Safety Mechanisms

- **Snapshots** — full module backup before any self-modification
- **Review gate** — all code changes must pass PM AI review
- **Syntax validation** — AST parsing before code application
- **Retry limits** — max 3 retries per failed task
- **Graceful shutdown** — `Ctrl+C` stops after the current cycle
- **Incremental indexing** — only changed files are re-embedded

## License

MIT License — see [LICENSE](LICENSE)
