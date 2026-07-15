"""Conector Ruvic para Telegram (Bot API)."""

from .client import TelegramClient
from .config import ENV_PREFIX, TelegramConfig
from .exceptions import (
    TelegramAuthError,
    TelegramConnectorError,
    TelegramDataError,
    TelegramNetworkError,
    TelegramRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "TelegramAuthError",
    "TelegramClient",
    "TelegramConfig",
    "TelegramConnectorError",
    "TelegramDataError",
    "TelegramNetworkError",
    "TelegramRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
