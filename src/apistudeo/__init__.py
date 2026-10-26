"""Cliente Python não oficial para a API do Studeo (EAD da Unicesumar)."""

from importlib.metadata import version

from apistudeo.exceptions import (
    AuthenticationError,
    RateLimitError,
    StudeoAPIError,
    StudeoError,
)

__version__ = version("apistudeo")

__all__ = [
    "AuthenticationError",
    "RateLimitError",
    "StudeoAPIError",
    "StudeoError",
    "__version__",
]
