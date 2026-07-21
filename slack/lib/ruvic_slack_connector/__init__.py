"""Conector Ruvic para Slack (Web API)."""

from .client import SlackClient
from .config import ENV_PREFIX, SlackConfig
from .exceptions import (
    SlackAuthError,
    SlackConnectorError,
    SlackDataError,
    SlackNetworkError,
    SlackRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "SlackAuthError",
    "SlackClient",
    "SlackConfig",
    "SlackConnectorError",
    "SlackDataError",
    "SlackNetworkError",
    "SlackRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
