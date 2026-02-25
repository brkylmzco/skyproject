import pytest
import logging
from unittest.mock import patch
from skyproject.pm_ai.reviewer import Reviewer
from skyproject.pm_ai.common import ErrorCode

@patch('logging.error')
def test_reviewer_logging(mock_logging_error):
    reviewer = Reviewer()
    task = {'id': 'task1'}
    with pytest.raises(Exception):
        reviewer.review_task(task)
    mock_logging_error.assert_called_with("%s - Error reviewing task %s: %s", ErrorCode.REVIEWER_ERROR.value, 'task1', 'Exception message', exc_info=True)
