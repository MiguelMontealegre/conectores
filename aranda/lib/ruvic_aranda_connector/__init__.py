"""Conector Ruvic para Aranda ASMS (API v9)."""

from .client import ArandaClient
from .config import ENV_PREFIX, ArandaConfig
from .exceptions import (
    ArandaAuthError,
    ArandaConnectorError,
    ArandaDataError,
    ArandaNetworkError,
    ArandaRateLimitError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "ArandaAuthError",
    "ArandaClient",
    "ArandaConfig",
    "ArandaConnectorError",
    "ArandaDataError",
    "ArandaNetworkError",
    "ArandaRateLimitError",
    "setup_logging",
]

__version__ = "1.0.0"
