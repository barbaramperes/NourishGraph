"""
app/observability/__init__.py

Observability & Tracing Module

Provides comprehensive monitoring for the AI pipeline:
- Span tracking and trace management
- Metrics collection (latency, tokens, costs)
- Prometheus-compatible export
"""

from app.observability.tracing import (
    Span,
    Trace,
    MetricsCollector,
    Tracer,
    get_tracer,
)

__all__ = [
    "Span",
    "Trace",
    "MetricsCollector",
    "Tracer",
    "get_tracer",
]
