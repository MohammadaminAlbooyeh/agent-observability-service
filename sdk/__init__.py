"""Thin client library for sending traces to the observability service."""

from .client import ObservabilityClient
from .tracer import Span, Tracer

__all__ = ["ObservabilityClient", "Span", "Tracer"]
