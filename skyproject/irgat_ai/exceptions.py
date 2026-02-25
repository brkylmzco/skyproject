"""IrgatAI custom exceptions."""


class FileOperationException(Exception):
    """Base exception for file operation errors."""


class FileNotFoundErrorException(FileOperationException):
    pass


class PermissionDeniedException(FileOperationException):
    pass


class IsADirectoryException(FileOperationException):
    pass


class SyntaxErrorException(Exception):
    """Raised when code has syntax errors."""


class ImportErrorException(Exception):
    """Raised when code has import errors."""


class CoderError(Exception):
    """Raised when the coder encounters an unexpected error."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original


class JSONDecodeError(Exception):
    """Raised when JSON decoding fails."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original
