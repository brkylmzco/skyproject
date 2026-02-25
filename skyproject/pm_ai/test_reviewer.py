import pytest
from skyproject.pm_ai.reviewer import Reviewer
from skyproject.pm_ai.common import ErrorCode
from unittest.mock import patch
import requests

@pytest.fixture
def sample_task():
    return {
        'id': 'task1',
        'content': {
            'operation': 'add',
            'operand1': 5,
            'operand2': 3,
            'dependencies': [],
            'estimated_time': 2
        }
    }

@pytest.fixture
def task_with_logical_error():
    return {
        'id': 'task2',
        'content': {
            'operation': 'divide',
            'operand1': 5,
            'operand2': 0
        }
    }

@pytest.fixture
def task_without_goals():
    return {
        'id': 'task3',
        'content': {
            'operation': 'add',
            'operand1': 5,
            'operand2': 3
        }
    }

@pytest.fixture
def task_with_circular_dependency():
    return {
        'id': 'task4',
        'content': {
            'operation': 'add',
            'dependencies': ['task4'],
            'estimated_time': 3
        }
    }

@pytest.fixture
def task_with_negative_estimated_time():
    return {
        'id': 'task5',
        'content': {
            'operation': 'subtract',
            'operand1': 10,
            'operand2': 5,
            'estimated_time': -1
        }
    }

@pytest.mark.parametrize('method,task', [
    ('check_completeness', {'content': None}),
    ('check_completeness', {'id': 'task1'}),
    ('check_logical_correctness', task_with_logical_error()),
    ('check_circular_dependencies', task_with_circular_dependency()),
    ('check_estimated_time', task_with_negative_estimated_time()),
])
def test_reviewer_raises_value_error(method, task):
    reviewer = Reviewer()
    with pytest.raises(ValueError):
        getattr(reviewer, method)(task)

@patch('logging.error')
def test_logging_on_value_error(mock_logging_error, task_with_logical_error):
    reviewer = Reviewer()
    with pytest.raises(ValueError):
        reviewer.check_completeness(task_with_logical_error)
    mock_logging_error.assert_any_call(
        ErrorCode.REVIEWER_SPECIFIC_ERROR.value,
        'A value error occurred.',
        task_with_logical_error.get('id'),
        pytest.mock.ANY,
        task_with_logical_error
    )

@patch('logging.error')
def test_logging_on_key_error(mock_logging_error):
    reviewer = Reviewer()
    task_missing_key = {'content': {}}
    with pytest.raises(KeyError):
        reviewer.check_completeness(task_missing_key)
    mock_logging_error.assert_any_call(
        ErrorCode.REVIEWER_ERROR.value,
        'A key error occurred.',
        task_missing_key.get('id', 'unknown'),
        pytest.mock.ANY,
        task_missing_key
    )

@patch('logging.error')
def test_logging_on_general_exception(mock_logging_error):
    reviewer = Reviewer()
    task_invalid = None
    with pytest.raises(Exception):
        reviewer.check_completeness(task_invalid)
    mock_logging_error.assert_any_call(
        ErrorCode.REVIEWER_ERROR.value,
        'An unspecified error occurred during task completeness check.',
        'unknown',
        pytest.mock.ANY,
        task_invalid
    )

@patch('logging.warning')
@patch('logging.error')
@patch('requests.get', side_effect=requests.exceptions.ConnectionError)
def test_attempt_recovery(mock_requests, mock_logging_error, mock_logging_warning, sample_task):
    reviewer = Reviewer()
    reviewer._attempt_recovery(sample_task)
    mock_logging_warning.assert_any_call(
        'Recovery attempt 1 failed for task task1: ',
        pytest.mock.ANY
    )
    mock_logging_error.assert_any_call(
        'All recovery attempts failed for task task1'
    )

def test_review_task(sample_task):
    reviewer = Reviewer()
    try:
        reviewer.check_completeness(sample_task)
    except Exception as e:
        pytest.fail(f'Review task raised an exception: {e}')
