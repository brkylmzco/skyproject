from __future__ import annotations

import logging
from typing import Dict, Tuple

from skyproject.core.config import Config
from skyproject.shared.file_ops import save_snapshot, write_file
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import CodeChange, ImprovementProposal

logger = logging.getLogger(__name__)


class PMSelfImprover:
    """PM AI analyzes and improves its own code using vector-search for cost efficiency."""

    def __init__(self, llm: LLMClient, code_index=None):
        self.llm = llm
        self._code_index = code_index

    @property
    def code_index(self):
        if self._code_index is None:
            from skyproject.core.code_index import CodeIndex
            self._code_index = CodeIndex()
        return self._code_index

    async def analyze_self(self) -> list[ImprovementProposal]:
        """Analyze PM AI code via vector search — only fetches relevant chunks, not all source."""
        try:
            self.code_index.ensure_indexed()

            module_summary = self.code_index.get_module_summary("pm_ai")

            improvement_areas = [
                "planning strategy and task creation logic",
                "code review criteria and quality checks",
                "task prioritization algorithm",
                "communication patterns with IrgatAI via MessageBus",
                "error handling and resilience",
            ]

            relevant_context = ""
            for area in improvement_areas:
                ctx = self.code_index.get_context_for_task(area, module="pm_ai", max_tokens=600)
                if ctx:
                    relevant_context += f"\n## Area: {area}\n{ctx}\n"

            prompt = f"""Analyze the PM AI module and propose specific improvements.

Module structure:
{module_summary}

Relevant code sections:
{relevant_context}

Focus on improving:
1. Planning strategies
2. Review criteria
3. Task prioritization
4. Communication with IrgatAI
5. Self-improvement techniques

For each improvement, provide detailed code changes.

Respond with JSON:
{{
    "proposals": [
        {{
            "title": "improvement title",
            "description": "what and why",
            "rationale": "expected benefit",
            "estimated_impact": "low/medium/high",
            "changes": [
                {{
                    "file_path": "skyproject/pm_ai/some_file.py",
                    "new_content": "complete new file content",
                    "change_type": "modify"
                }}
            ]
        }}
    ]
}}
"""

            result = await self.llm.generate_json(Config.PM_SYSTEM_PROMPT, prompt)
            proposals = []
            for p in result.get("proposals", []):
                changes = [
                    CodeChange(
                        file_path=c["file_path"],
                        new_content=c["new_content"],
                        change_type=c.get("change_type", "modify"),
                    )
                    for c in p.get("changes", [])
                ]
                proposals.append(ImprovementProposal(
                    source="pm_ai",
                    target="pm_ai",
                    title=p["title"],
                    description=p["description"],
                    rationale=p.get("rationale", ""),
                    estimated_impact=p.get("estimated_impact", "medium"),
                    proposed_changes=changes,
                ))
            logger.info("Generated %d PM improvement proposals", len(proposals))
            return proposals
        except Exception as e:
            logger.error("PM self analysis failed: %s", e)
            return []

    async def apply_improvement(self, proposal: ImprovementProposal) -> bool:
        """Apply an approved improvement, with snapshot for rollback."""
        await save_snapshot("skyproject/pm_ai", f"pm_pre_{proposal.id}")

        try:
            for change in proposal.proposed_changes:
                await write_file(change.file_path, change.new_content)
                self.code_index.index_file(change.file_path, change.new_content)
            proposal.status = "implemented"
            return True
        except Exception as e:
            logger.error("Failed to apply PM improvement: %s", e)
            proposal.status = "rejected"
            return False
