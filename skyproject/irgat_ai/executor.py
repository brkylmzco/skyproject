import os
import aiofiles
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from skyproject.irgat_ai.exceptions import FileOperationException, FileNotFoundErrorException, PermissionDeniedException, IsADirectoryException

logger = logging.getLogger(__name__)

async def _handle_file_error(e, context):
    if isinstance(e, FileNotFoundError):
        logger.error('File not found: %s', context['file_path'], exc_info=True, extra=context)
        raise FileNotFoundErrorException('File not found')
    elif isinstance(e, PermissionError):
        logger.error('Permission denied: %s', context['file_path'], exc_info=True, extra=context)
        raise PermissionDeniedException('Permission denied')
    elif isinstance(e, IsADirectoryError):
        logger.error('Expected a file but found a directory: %s', context['file_path'], exc_info=True, extra=context)
        raise IsADirectoryException('Is a directory error')
    else:
        logger.error('Unexpected error: %s', e, exc_info=True, extra=context)
        raise FileOperationException('Unexpected error')

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
async def _read_file(self, file_path: str) -> str:
    try:
        async with aiofiles.open(file_path, 'r') as f:
            return await f.read()
    except Exception as e:
        _handle_file_error(e, {'context': '_read_file', 'file_path': file_path})