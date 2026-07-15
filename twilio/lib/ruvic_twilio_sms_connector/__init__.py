"""Conector Ruvic para Twilio SMS (Programmable Messaging)."""

from .client import TwilioSmsClient
from .config import ENV_PREFIX, TwilioSmsConfig
from .exceptions import (
    TwilioSmsAuthError,
    TwilioSmsConnectorError,
    TwilioSmsDataError,
    TwilioSmsNetworkError,
    TwilioSmsRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "TwilioSmsAuthError",
    "TwilioSmsClient",
    "TwilioSmsConfig",
    "TwilioSmsConnectorError",
    "TwilioSmsDataError",
    "TwilioSmsNetworkError",
    "TwilioSmsRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
