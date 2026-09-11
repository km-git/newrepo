"""Broker adapters — paper, ccxt (Kraken/OKX), optional kraken-cli."""

from engine.broker.factory import get_broker, execution_mode

__all__ = ["get_broker", "execution_mode"]
