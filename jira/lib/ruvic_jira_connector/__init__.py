"""Conector Ruvic para Jira Cloud (REST API v3)."""

from .client import JiraClient
from .config import ENV_PREFIX, JiraConfig
from .exceptions import (
    JiraAuthError,
    JiraConnectorError,
    JiraDataError,
    JiraNetworkError,
    JiraRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "JiraAuthError",
    "JiraClient",
    "JiraConfig",
    "JiraConnectorError",
    "JiraDataError",
    "JiraNetworkError",
    "JiraRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
