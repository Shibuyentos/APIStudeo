"""Cliente Python não oficial para a API do Studeo (EAD da Unicesumar)."""

from importlib.metadata import version

from apistudeo.client import StudeoClient
from apistudeo.exceptions import (
    AuthenticationError,
    RateLimitError,
    StudeoAPIError,
    StudeoError,
)
from apistudeo.models import (
    Announcement,
    AuthInfo,
    Course,
    Deadline,
    Discipline,
    Grade,
    ServerTime,
    StudyEvent,
    User,
)

__version__ = version("apistudeo")

__all__ = [
    "Announcement",
    "AuthInfo",
    "AuthenticationError",
    "Course",
    "Deadline",
    "Discipline",
    "Grade",
    "RateLimitError",
    "ServerTime",
    "StudeoAPIError",
    "StudeoClient",
    "StudeoError",
    "StudyEvent",
    "User",
    "__version__",
]
