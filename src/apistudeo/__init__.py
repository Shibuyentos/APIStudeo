"""Cliente Python não oficial para a API do Studeo (EAD da Unicesumar)."""

from importlib.metadata import version

from apistudeo.client import StudeoClient
from apistudeo.exceptions import (
    AuthenticationError,
    RateLimitError,
    StudeoAPIError,
    StudeoError,
)
from apistudeo.models import AuthInfo

__version__ = version("apistudeo")

__all__ = [
    "AuthInfo",
    "AuthenticationError",
    "RateLimitError",
    "StudeoAPIError",
    "StudeoClient",
    "StudeoError",
    "__version__",
]
