class DocMindError(Exception):
    """Base class for expected application errors."""


class InvalidPDFError(DocMindError):
    """Raised when a file cannot be parsed as a PDF."""
