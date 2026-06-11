"""
app/observability/tracing.py

Agent Observability & Tracing System

Comprehensive monitoring for debugging and optimization.
Based on Microsoft Agent Framework 2025 best practices.

Features:
- Latency tracking per component
- Token usage and cost tracking
- Cache hit rates
- Tool call success rates
- Agent confidence scores
- Exportable metrics (Prometheus-compatible)
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
import time
import threading
import json
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Span:
    """A single traced operation."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    parent_id: Optional[str] = None
    span_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"  # running, success, error
    error: Optional[str] = None
    
    def __post_init__(self):
        import uuid
        if not self.span_id:
            self.span_id = str(uuid.uuid4())[:8]
    
    def finish(self, status: str = "success", error: str = None):
        """Mark span as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
    
    def add_event(self, name: str, data: Dict[str, Any] = None):
        """Add event to span."""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "data": data or {}
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "events": self.events
        }


@dataclass
class Trace:
    """A complete trace containing multiple spans."""
    trace_id: str
    user_id: Optional[int] = None
    query: Optional[str] = None
    spans: List[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_span(self, span: Span):
        """Add span to trace."""
        self.spans.append(span)
    
    def finish(self):
        """Mark trace as finished."""
        self.end_time = time.time()
    
    @property
    def total_duration_ms(self) -> float:
        """Total trace duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "query": self.query,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans]
        }


# ============================================================
# METRICS COLLECTOR
# ============================================================

class MetricsCollector:
    """
    Collects and aggregates metrics across all requests.
    Thread-safe for concurrent access.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._reset()
    
    def _reset(self):
        """Reset all metrics."""
        self.metrics = {
            # Latency metrics (in ms)
            "latency": {
                "total": [],
                "routing": [],
                "retrieval": [],
                "generation": [],
                "tools": []
            },
            # Token metrics
            "tokens": {
                "input": 0,
                "output": 0,
                "total": 0,
                "embedding": 0
            },
            # Cache metrics
            "cache": {
                "hits": 0,
                "misses": 0
            },
            # Tool metrics
            "tools": {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "by_name": {}
            },
            # Agent metrics
            "agents": {
                "by_name": {},
                "total_requests": 0
            },
            # Quality metrics
            "quality": {
                "confidence_scores": [],
                "retrieval_counts": [],
                "thumbs_up": 0,
                "thumbs_down": 0
            },
            # Error metrics
            "errors": {
                "count": 0,
                "by_type": {}
            },
            # Complexity distribution
            "complexity": {
                "simple": 0,
                "moderate": 0,
                "complex": 0
            }
        }
    
    def record_latency(self, component: str, duration_ms: float):
        """Record latency for a component."""
        with self._lock:
            if component in self.metrics["latency"]:
                self.metrics["latency"][component].append(duration_ms)
                # Keep only last 1000 entries
                if len(self.metrics["latency"][component]) > 1000:
                    self.metrics["latency"][component] = self.metrics["latency"][component][-1000:]
    
    def record_tokens(self, input_tokens: int = 0, output_tokens: int = 0, embedding_tokens: int = 0):
        """Record token usage."""
        with self._lock:
            self.metrics["tokens"]["input"] += input_tokens
            self.metrics["tokens"]["output"] += output_tokens
            self.metrics["tokens"]["total"] += input_tokens + output_tokens
            self.metrics["tokens"]["embedding"] += embedding_tokens
    
    def record_cache(self, hit: bool):
        """Record cache hit or miss."""
        with self._lock:
            if hit:
                self.metrics["cache"]["hits"] += 1
            else:
                self.metrics["cache"]["misses"] += 1
    
    def record_tool_call(self, tool_name: str, success: bool, duration_ms: float = 0):
        """Record tool call."""
        with self._lock:
            self.metrics["tools"]["calls"] += 1
            if success:
                self.metrics["tools"]["successes"] += 1
            else:
                self.metrics["tools"]["failures"] += 1
            
            if tool_name not in self.metrics["tools"]["by_name"]:
                self.metrics["tools"]["by_name"][tool_name] = {"calls": 0, "successes": 0, "total_ms": 0}
            
            self.metrics["tools"]["by_name"][tool_name]["calls"] += 1
            if success:
                self.metrics["tools"]["by_name"][tool_name]["successes"] += 1
            self.metrics["tools"]["by_name"][tool_name]["total_ms"] += duration_ms
    
    def record_agent(self, agent_name: str, duration_ms: float, success: bool):
        """Record agent execution."""
        with self._lock:
            self.metrics["agents"]["total_requests"] += 1
            
            if agent_name not in self.metrics["agents"]["by_name"]:
                self.metrics["agents"]["by_name"][agent_name] = {
                    "calls": 0,
                    "successes": 0,
                    "total_ms": 0
                }
            
            self.metrics["agents"]["by_name"][agent_name]["calls"] += 1
            if success:
                self.metrics["agents"]["by_name"][agent_name]["successes"] += 1
            self.metrics["agents"]["by_name"][agent_name]["total_ms"] += duration_ms
    
    def record_quality(self, confidence: float = None, retrieval_count: int = None, feedback: str = None):
        """Record quality metrics."""
        with self._lock:
            if confidence is not None:
                self.metrics["quality"]["confidence_scores"].append(confidence)
                if len(self.metrics["quality"]["confidence_scores"]) > 1000:
                    self.metrics["quality"]["confidence_scores"] = self.metrics["quality"]["confidence_scores"][-1000:]
            
            if retrieval_count is not None:
                self.metrics["quality"]["retrieval_counts"].append(retrieval_count)
            
            if feedback == "up":
                self.metrics["quality"]["thumbs_up"] += 1
            elif feedback == "down":
                self.metrics["quality"]["thumbs_down"] += 1
    
    def record_error(self, error_type: str):
        """Record error occurrence."""
        with self._lock:
            self.metrics["errors"]["count"] += 1
            if error_type not in self.metrics["errors"]["by_type"]:
                self.metrics["errors"]["by_type"][error_type] = 0
            self.metrics["errors"]["by_type"][error_type] += 1
    
    def record_complexity(self, complexity: str):
        """Record query complexity."""
        with self._lock:
            if complexity in self.metrics["complexity"]:
                self.metrics["complexity"][complexity] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary with computed statistics."""
        with self._lock:
            # Compute latency stats
            latency_stats = {}
            for component, values in self.metrics["latency"].items():
                if values:
                    sorted_vals = sorted(values)
                    latency_stats[component] = {
                        "avg_ms": sum(values) / len(values),
                        "p50_ms": sorted_vals[len(sorted_vals) // 2],
                        "p95_ms": sorted_vals[int(len(sorted_vals) * 0.95)] if len(sorted_vals) > 20 else sorted_vals[-1],
                        "p99_ms": sorted_vals[int(len(sorted_vals) * 0.99)] if len(sorted_vals) > 100 else sorted_vals[-1],
                        "count": len(values)
                    }
                else:
                    latency_stats[component] = {"avg_ms": 0, "count": 0}
            
            # Compute cache hit rate
            cache_total = self.metrics["cache"]["hits"] + self.metrics["cache"]["misses"]
            cache_hit_rate = self.metrics["cache"]["hits"] / max(cache_total, 1)
            
            # Compute tool success rate
            tool_success_rate = self.metrics["tools"]["successes"] / max(self.metrics["tools"]["calls"], 1)
            
            # Compute average confidence
            conf_scores = self.metrics["quality"]["confidence_scores"]
            avg_confidence = sum(conf_scores) / len(conf_scores) if conf_scores else 0
            
            # Compute costs (approximate)
            # GPT-4o-mini: $0.15/1M input, $0.60/1M output
            # Embeddings: $0.02/1M tokens
            input_cost = self.metrics["tokens"]["input"] * 0.00000015
            output_cost = self.metrics["tokens"]["output"] * 0.0000006
            embedding_cost = self.metrics["tokens"]["embedding"] * 0.00000002
            total_cost = input_cost + output_cost + embedding_cost
            
            return {
                "latency": latency_stats,
                "tokens": self.metrics["tokens"],
                "cost_usd": {
                    "input": round(input_cost, 6),
                    "output": round(output_cost, 6),
                    "embedding": round(embedding_cost, 6),
                    "total": round(total_cost, 6)
                },
                "cache": {
                    **self.metrics["cache"],
                    "hit_rate": round(cache_hit_rate, 4)
                },
                "tools": {
                    "total_calls": self.metrics["tools"]["calls"],
                    "success_rate": round(tool_success_rate, 4),
                    "by_name": self.metrics["tools"]["by_name"]
                },
                "agents": self.metrics["agents"],
                "quality": {
                    "avg_confidence": round(avg_confidence, 4),
                    "thumbs_up": self.metrics["quality"]["thumbs_up"],
                    "thumbs_down": self.metrics["quality"]["thumbs_down"],
                    "satisfaction_rate": self.metrics["quality"]["thumbs_up"] / 
                        max(self.metrics["quality"]["thumbs_up"] + self.metrics["quality"]["thumbs_down"], 1)
                },
                "errors": self.metrics["errors"],
                "complexity": self.metrics["complexity"]
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._reset()


# ============================================================
# TRACER
# ============================================================

class Tracer:
    """
    Main tracing interface for agent observability.
    
    Usage:
        tracer = get_tracer()
        
        with tracer.trace("chat_request", user_id=123) as trace:
            with trace.span("routing"):
                # routing logic
                pass
            
            with trace.span("retrieval"):
                # retrieval logic
                tracer.log_event("papers_found", count=5)
    """
    
    def __init__(self, enabled: bool = True, export_traces: bool = False):
        self.enabled = enabled
        self.export_traces = export_traces
        self.metrics = MetricsCollector()
        self._current_trace = threading.local()
        self._traces: List[Trace] = []
        self._max_traces = 100
    
    @contextmanager
    def trace(self, name: str, user_id: int = None, query: str = None, **metadata):
        """Start a new trace context."""
        if not self.enabled:
            yield DummyTrace()
            return
        
        import uuid
        trace = Trace(
            trace_id=str(uuid.uuid4())[:12],
            user_id=user_id,
            query=query,
            metadata=metadata
        )
        
        # Set as current trace
        self._current_trace.trace = trace
        
        try:
            yield TraceContext(trace, self)
        finally:
            trace.finish()
            self._current_trace.trace = None
            
            # Record total latency
            self.metrics.record_latency("total", trace.total_duration_ms)
            
            # Store trace
            if self.export_traces:
                self._traces.append(trace)
                if len(self._traces) > self._max_traces:
                    self._traces = self._traces[-self._max_traces:]
    
    @contextmanager
    def span(self, name: str, **metadata):
        """Start a new span within current trace."""
        if not self.enabled:
            yield DummySpan()
            return
        
        trace = getattr(self._current_trace, 'trace', None)
        parent_id = None
        
        if trace:
            # Get parent span if any
            if trace.spans:
                parent_id = trace.spans[-1].span_id
        
        span = Span(
            name=name,
            start_time=time.time(),
            parent_id=parent_id,
            metadata=metadata
        )
        
        try:
            yield span
            span.finish("success")
        except Exception as e:
            span.finish("error", str(e))
            raise
        finally:
            if trace:
                trace.add_span(span)
            
            # Record latency by component
            if span.duration_ms:
                component = name.split(".")[0]  # e.g., "routing.classify" -> "routing"
                if component in ["routing", "retrieval", "generation", "tools"]:
                    self.metrics.record_latency(component, span.duration_ms)
    
    def log_event(self, name: str, **data):
        """Log event to current span."""
        trace = getattr(self._current_trace, 'trace', None)
        if trace and trace.spans:
            trace.spans[-1].add_event(name, data)
    
    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent traces."""
        return [t.to_dict() for t in self._traces[-limit:]]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        return self.metrics.get_summary()


class TraceContext:
    """Context manager for trace operations."""
    
    def __init__(self, trace: Trace, tracer: Tracer):
        self.trace = trace
        self.tracer = tracer
    
    @contextmanager
    def span(self, name: str, **metadata):
        """Create a span within this trace."""
        with self.tracer.span(name, **metadata) as s:
            yield s
    
    def log_event(self, name: str, **data):
        """Log event to current span."""
        self.tracer.log_event(name, **data)
    
    def set_metadata(self, **metadata):
        """Set trace metadata."""
        self.trace.metadata.update(metadata)


class DummyTrace:
    """Dummy trace when tracing is disabled."""
    def span(self, name: str, **metadata):
        return DummySpanContext()
    def log_event(self, name: str, **data):
        pass
    def set_metadata(self, **metadata):
        pass


class DummySpan:
    """Dummy span when tracing is disabled."""
    def add_event(self, name: str, data: Dict = None):
        pass
    def finish(self, status: str = "success", error: str = None):
        pass


class DummySpanContext:
    """Context manager for dummy spans."""
    def __enter__(self):
        return DummySpan()
    def __exit__(self, *args):
        pass


# ============================================================
# DECORATOR FOR TRACING
# ============================================================

def trace_function(component: str = "general"):
    """
    Decorator to automatically trace function execution.
    
    Usage:
        @trace_function("retrieval")
        def search_papers(query: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.span(f"{component}.{func.__name__}"):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def trace_async_function(component: str = "general"):
    """Decorator to trace async functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.span(f"{component}.{func.__name__}"):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get singleton tracer instance."""
    global _tracer
    if _tracer is None:
        enabled = os.getenv("TRACING_ENABLED", "true").lower() == "true"
        export = os.getenv("TRACING_EXPORT", "false").lower() == "true"
        _tracer = Tracer(enabled=enabled, export_traces=export)
    return _tracer


def get_metrics() -> Dict[str, Any]:
    """Convenience function to get metrics."""
    return get_tracer().get_metrics()


# ============================================================
# PROMETHEUS EXPORT (Optional)
# ============================================================

def export_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus format.
    
    Can be exposed at /metrics endpoint for scraping.
    """
    metrics = get_metrics()
    lines = []
    
    # Latency metrics
    for component, stats in metrics.get("latency", {}).items():
        if isinstance(stats, dict) and "avg_ms" in stats:
            lines.append(f'nourishgraph_latency_avg_ms{{component="{component}"}} {stats["avg_ms"]:.2f}')
            lines.append(f'nourishgraph_latency_p95_ms{{component="{component}"}} {stats.get("p95_ms", 0):.2f}')
    
    # Token metrics
    tokens = metrics.get("tokens", {})
    lines.append(f'nourishgraph_tokens_total{{type="input"}} {tokens.get("input", 0)}')
    lines.append(f'nourishgraph_tokens_total{{type="output"}} {tokens.get("output", 0)}')
    
    # Cache metrics
    cache = metrics.get("cache", {})
    lines.append(f'nourishgraph_cache_hit_rate {cache.get("hit_rate", 0):.4f}')
    
    # Tool metrics
    tools = metrics.get("tools", {})
    lines.append(f'nourishgraph_tool_calls_total {tools.get("total_calls", 0)}')
    lines.append(f'nourishgraph_tool_success_rate {tools.get("success_rate", 0):.4f}')
    
    # Cost metrics
    cost = metrics.get("cost_usd", {})
    lines.append(f'nourishgraph_cost_usd_total {cost.get("total", 0):.6f}')
    
    # Error metrics
    errors = metrics.get("errors", {})
    lines.append(f'nourishgraph_errors_total {errors.get("count", 0)}')
    
    return "\n".join(lines)
