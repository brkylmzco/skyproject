import logging
from skyproject.pm_ai.common import ErrorCode
import networkx as nx
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class Reviewer:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def check_completeness(self, task, other_tasks=None):
        try:
            self._check_required_fields(task, ['id', 'content'])
            self._check_required_fields(task['content'], ['operation', 'operand1', 'operand2', 'estimated_time', 'dependencies'])
            self._check_logical_errors(task['content'])
            self._check_negative_estimated_time(task['content'])
            if other_tasks is not None:
                self._check_circular_dependencies(task, other_tasks)
        except ValueError as ve:
            self._log_error(ErrorCode.REVIEWER_SPECIFIC_ERROR, 'ValueError', task.get('id', 'unknown'), ve, task)
            raise
        except KeyError as ke:
            self._log_error(ErrorCode.REVIEWER_ERROR, 'KeyError', task.get('id', 'unknown'), ke, task)
            raise
        except nx.NetworkXError as ne:
            self._log_error(ErrorCode.REVIEWER_ERROR, 'NetworkXError', task.get('id', 'unknown'), ne, task)
            raise
        except (ConnectionError, Timeout, HTTPError) as ne:
            self._log_error(ErrorCode.REVIEWER_ERROR, 'Network-related error', task.get('id', 'unknown'), ne, task)
            self._attempt_recovery(task)
        except Exception as e:
            self._log_error(ErrorCode.REVIEWER_ERROR, 'Error checking completeness', task.get('id', 'unknown'), e, task)
            raise

    def _log_error(self, error_code, message, task_id, error, task):
        error_messages = {
            'ValueError': 'A value error occurred.',
            'KeyError': 'A key error occurred.',
            'NetworkXError': 'A network graph error occurred.',
            'Network-related error': 'A network-related error occurred.',
            'Error checking completeness': 'An unspecified error occurred during task completeness check.'
        }
        log_message = error_messages.get(message, 'An unknown error occurred.')
        logging.error(
            "%s - %s for task %s: %s | Task content: %s | Task metadata: %s",
            error_code.value,
            log_message,
            task_id,
            str(error),
            str(task.get('content', {})),
            str(task.get('metadata', {})),
            exc_info=True
        )

    def _attempt_recovery(self, task):
        recovery_attempts = 3
        for attempt in range(recovery_attempts):
            try:
                # Simulate a recovery process
                logging.warning(f'Recovery attempt {attempt + 1} for task {task.get("id", "unknown")}')
                time.sleep(2)  # Simulate wait time for recovery
                # Simulate successful recovery
                return
            except Exception as e:
                logging.warning(f'Recovery attempt {attempt + 1} failed for task {task.get("id", "unknown")}: {str(e)}')
        logging.error(f'All recovery attempts failed for task {task.get("id", "unknown")}.')
