import ast
import traceback
import logging
import asyncio
from skyproject.irgat_ai.exceptions import SyntaxErrorException, ImportErrorException, FileOperationException

logger = logging.getLogger(__name__)

class Tester:
    async def validate_changes(self, changes: list[CodeChange]) -> bool:
        async def check_syntax_and_imports(source_code: str) -> bool:
            try:
                ast.parse(source_code)
                return True
            except SyntaxError as e:
                raise SyntaxErrorException(f'Syntax error at line {e.lineno} offset {e.offset}') from e
            except ImportError as e:
                raise ImportErrorException(f'Import error: {str(e)}') from e
            except Exception as e:
                logger.error('Unexpected error during syntax and import check: %s', e, exc_info=True)
                raise FileOperationException('Unexpected error during syntax and import check')

        tasks = [check_syntax_and_imports(change.new_content) for change in changes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for change, result in zip(changes, results):
            if isinstance(result, Exception):
                self._log_error(result, {'source_code': change.new_content})

        return all(isinstance(result, bool) and result for result in results)

    def _log_error(self, e: Exception, context: dict) -> None:
        error_info = {
            'error_type': type(e).__name__,
            'filename': getattr(e, 'filename', ''),
            'lineno': getattr(e, 'lineno', ''),
            'message': str(e),
            'context': context
        }
        logger.error('Error occurred', extra=error_info)
        logger.debug(traceback.format_exc())