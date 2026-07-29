"""Stock provider implementations."""
from __future__ import annotations

from .toss import TossStockClient


def __getattr__(name: str):
    if name == "KisStockClient":
        from .kis import KisStockClient

        return KisStockClient
    raise AttributeError(name)


__all__ = ["KisStockClient", "TossStockClient"]