import pytest
import asyncio
from unittest.mock import patch, MagicMock
from skyproject.irgat_ai.executor import Executor
from skyproject.shared.models import CodeChange


@pytest.mark.asyncio
async def test_apply_changes_success():
    executor = Executor()
    changes = [
        CodeChange(file_path='test_file_1.py', new_content='content 1', change_type='modify'),
        CodeChange(file_path='test_file_2.py', new_content='content 2', change_type='modify')
    ]

    with patch('skyproject.irgat_ai.executor.Executor._read_file', return_value='old content'), \
         patch('skyproject.irgat_ai.executor.Executor._write_file', return_value=None) as mock_write_file:
        success, message = await executor._apply_changes(changes)

    assert success is True
    assert message == ''
    assert mock_write_file.call_count == 2


@pytest.mark.asyncio
async def test_apply_changes_fails_and_rolls_back():
    executor = Executor()
    changes = [
        CodeChange(file_path='test_file_1.py', new_content='content 1', change_type='modify'),
        CodeChange(file_path='test_file_2.py', new_content='content 2', change_type='modify')
    ]

    with patch('skyproject.irgat_ai.executor.Executor._read_file', return_value='old content'), \
         patch('skyproject.irgat_ai.executor.Executor._write_file', side_effect=Exception('Write error')) as mock_write_file, \
         patch('skyproject.irgat_ai.executor.Executor._rollback_changes') as mock_rollback:

        success, message = await executor._apply_changes(changes)

    assert success is False
    assert 'Write error' in message
    assert mock_write_file.call_count == 1
    mock_rollback.assert_called_once()


@pytest.mark.asyncio
async def test_rollback_changes_success():
    executor = Executor()
    backup_files = {
        'test_file_1.py': 'old content 1',
        'test_file_2.py': 'old content 2'
    }

    with patch('skyproject.irgat_ai.executor.Executor._write_file', return_value=None) as mock_write_file:
        await executor._rollback_changes(backup_files)

    assert mock_write_file.call_count == 2


@pytest.mark.asyncio
async def test_rollback_changes_fails_logs_error():
    executor = Executor()
    backup_files = {
        'test_file_1.py': 'old content 1'
    }

    with patch('skyproject.irgat_ai.executor.Executor._write_file', side_effect=Exception('Rollback error')) as mock_write_file, \
         patch('logging.Logger.error') as mock_log_error:

        await executor._rollback_changes(backup_files)

    assert mock_write_file.call_count == 1
    mock_log_error.assert_called()


@pytest.mark.asyncio
async def test_retry_operation_success_after_failure():
    executor = Executor()

    async def mock_operation():
        if mock_operation.call_count < 2:
            mock_operation.call_count += 1
            raise Exception('Temporary failure')
        return 'success'

    mock_operation.call_count = 0

    with patch('asyncio.sleep', return_value=None):
        result = await executor._retry_operation(mock_operation, retries=3, delay=0.1)

    assert result == 'success'
    assert mock_operation.call_count == 2


@pytest.mark.asyncio
async def test_retry_operation_fails_after_max_retries():
    executor = Executor()

    async def mock_operation():
        raise Exception('Persistent failure')

    with patch('asyncio.sleep', return_value=None), \
         patch('logging.Logger.error') as mock_log_error:
        with pytest.raises(Exception, match='Persistent failure'):
            await executor._retry_operation(mock_operation, retries=3, delay=0.1)

    assert mock_log_error.call_count == 1
