import logging
from enum import Enum
import inspect
from typing import Optional

# Configure logging with a default format and level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SkyProjectLogger')

class ErrorCode(Enum):
    UNKNOWN_PROVIDER = "ERR001"
    OPENAI_GENERATION_ERROR = "ERR002"
    ANTHROPIC_GENERATION_ERROR = "ERR003"
    JSON_DECODE_ERROR = "ERR004"
    MAX_RETRIES_REACHED = "ERR005"
    FCM_API_ERROR = "ERR006"
    UNREGISTERED_TOKEN = "ERR007"
    GENERAL_NOTIFICATION_ERROR = "ERR008"
    DEVICE_REGISTRATION_FAILED = "ERR010"
    TOKEN_RETRIEVAL_ERROR = "ERR011"
    NETWORK_ERROR = "ERR012"
    TIMEOUT_ERROR = "ERR013"
    HTTP_ERROR = "ERR014"
    REQUEST_EXCEPTION = "ERR015"


def _get_current_context() -> str:
    """Retrieve the current function name and contextual parameters."""
    frame = inspect.currentframe().f_back
    function_name = frame.f_code.co_name
    arg_info = inspect.getargvalues(frame)
    args = {arg: arg_info.locals[arg] for arg in arg_info.args}
    return f"Function: {function_name}, Args: {args}"


def log_error(code: ErrorCode, message: str, exc_info: Optional[bool] = True):
    context = _get_current_context()
    logger.error("%s - %s | Context: %s", code.value, message, context, exc_info=exc_info)


def log_warning(message: str, exc_info: Optional[bool] = True):
    context = _get_current_context()
    logger.warning("%s | Context: %s", message, context, exc_info=exc_info)


def log_info(message: str):
    context = _get_current_context()
    logger.info("%s | Context: %s", message, context)


def configure_logging(level: int = logging.INFO, format: str = '%(asctime)s - %(levelname)s - %(message)s'):
    """Allows dynamic configuration of the logging level and format."""
    logging.basicConfig(level=level, format=format)
    logger.setLevel(level)
