"""Thin client library for sending traces to the observability service."""

from src.sdk.tracer import Tracer
from src.sdk.client import ObservabilityClient

__all__ = ["Tracer", "ObservabilityClient"]
