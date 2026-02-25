"""Code validation and testing for IrgatAI."""
from __future__ import annotations

import ast
import asyncio
import logging
import traceback

from skyproject.shared.models import CodeChange

logger = logging.getLogger(__name__)


class Tester:
    """Validates code changes before they are applied."""

    async def validate_changes(self, changes: list[CodeChange]) -> bool:
        """Validate all code changes via syntax checking."""
        if not changes:
            return False

        tasks = [self._check_syntax(change) for change in changes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_valid = True
        for change, result in zip(changes, results):
            if isinstance(result, Exception):
                logger.error(
                    "Validation failed for %s: %s",
                    change.file_path, result,
                )
                all_valid = False
            elif not result:
                all_valid = False

        return all_valid

    async def _check_syntax(self, change: CodeChange) -> bool:
        """Check if the code has valid Python syntax."""
        if not change.file_path.endswith(".py"):
            return True

        try:
            ast.parse(change.new_content)
            return True
        except SyntaxError as e:
            logger.warning(
                "Syntax error in %s at line %s: %s",
                change.file_path, e.lineno, e.msg,
            )
            return False
        except Exception as e:
            logger.error("Unexpected validation error: %s", e, exc_info=True)
            return False
