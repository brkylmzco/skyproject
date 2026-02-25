from __future__ import annotations

import logging

from tenacity import retry, stop_after_attempt, wait_exponential

from skyproject.core.config import Config
from skyproject.shared.file_ops import save_snapshot, write_file
from skyproject.shared.llm_client import LLMClient
from skyproject.shared.models import CodeChange, ImprovementProposal

logger = logging.getLogger(__name__)


class IrgatSelfImprover:
    """IrgatAI analyzes and improves its own code using vector-search for cost efficiency."""

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
        """Analyze IrgatAI code via vector search — only fetches relevant chunks."""
        try:
            self.code_index.ensure_indexed()

            module_summary = self.code_index.get_module_summary("irgat_ai")

            improvement_areas = [
                "code generation strategy and implementation patterns",
                "task execution and error recovery logic",
                "testing and validation capabilities",
                "self-improvement and anomaly detection",
                "feedback processing and revision workflow",
            ]

            relevant_context = ""
            for area in improvement_areas:
                ctx = self.code_index.get_context_for_task(area, module="irgat_ai", max_tokens=600)
                if ctx:
                    relevant_context += f"\n## Area: {area}\n{ctx}\n"

            prompt = f"""Analyze the IrgatAI module and propose specific improvements.

Module structure:
{module_summary}

Relevant code sections:
{relevant_context}

Identify 1-3 concrete improvements. Focus on:
1. Better code generation strategies
2. Smarter implementation patterns
3. More robust error handling
4. Better testing capabilities
5. More effective self-improvement

For each improvement, provide EXACT code changes.

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
                    "file_path": "skyproject/irgat_ai/some_file.py",
                    "new_content": "complete new file content",
                    "change_type": "modify"
                }}
            ]
        }}
    ]
}}"""

            result = await self.llm.generate_json(Config.IRGAT_SYSTEM_PROMPT, prompt)
            proposals = self._parse_proposals(result)
            return proposals
        except Exception as e:
            logger.error("Irgat self analysis failed: %s", e, exc_info=True)
            return []

    def _parse_proposals(self, result: dict) -> list[ImprovementProposal]:
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
                source="irgat_ai",
                target="irgat_ai",
                title=p["title"],
                description=p["description"],
                rationale=p.get("rationale", ""),
                estimated_impact=p.get("estimated_impact", "medium"),
                proposed_changes=changes,
            ))
        logger.info("Generated %d Irgat improvement proposals", len(proposals))
        return proposals

    async def apply_improvement(self, proposal: ImprovementProposal) -> bool:
        """Apply an improvement with safety snapshot and re-index."""
        await save_snapshot("skyproject/irgat_ai", f"irgat_pre_{proposal.id}")

        try:
            for change in proposal.proposed_changes:
                await self._execute_with_retry(write_file, change.file_path, change.new_content)
                self.code_index.index_file(change.file_path, change.new_content)
            proposal.status = "implemented"
            return True
        except FileNotFoundError as e:
            logger.error("File not found during improvement: %s", e, exc_info=True)
            proposal.status = "rejected"
            return False
        except PermissionError as e:
            logger.error("Permission denied during improvement: %s", e, exc_info=True)
            proposal.status = "rejected"
            return False
        except Exception as e:
            logger.error("Error applying improvement '%s': %s", proposal.title, e, exc_info=True)
            proposal.status = "rejected"
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def _execute_with_retry(self, func, *args, **kwargs):
        return await func(*args, **kwargs)
