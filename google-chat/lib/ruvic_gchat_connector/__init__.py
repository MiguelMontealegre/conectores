"""Conector Ruvic para Google Chat (mensajería a espacios)."""

from .client import GchatClient
from .config import ENV_PREFIX, GchatConfig
from .exceptions import (
    GchatAuthError,
    GchatConnectorError,
    GchatDataError,
    GchatNetworkError,
    GchatRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "GchatAuthError",
    "GchatClient",
    "GchatConfig",
    "GchatConnectorError",
    "GchatDataError",
    "GchatNetworkError",
    "GchatRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
