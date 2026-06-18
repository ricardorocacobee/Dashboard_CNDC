"""Project exceptions."""


class CNDCExtractorError(Exception):
    """Base exception for expected extractor failures."""


class ConfigurationError(CNDCExtractorError):
    """Raised when configuration is invalid."""


class HTTPClientError(CNDCExtractorError):
    """Raised when the HTTP client cannot fetch valid JSON."""


class HARClientError(CNDCExtractorError):
    """Raised when HAR input cannot satisfy a request."""


class DateSelectionError(CNDCExtractorError):
    """Raised when no valid operation date can be selected."""


class NormalizationError(CNDCExtractorError):
    """Raised when a response cannot be normalized."""
