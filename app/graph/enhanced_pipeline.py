"""
app/graph/enhanced_pipeline.py

Enhanced RAG Pipeline with Advanced Features

Integrates:
- Adaptive RAG (Jeong et al., 2024) - Query complexity classification
- Observability & Tracing (Microsoft 2025) - Comprehensive monitoring

Usage:
    from app.graph.enhanced_pipeline import EnhancedPipeline
    
    pipeline = EnhancedPipeline()
    result = await pipeline.run(
        query="What are the benefits of vitamin D?",
        user_profile={"goal": "health"}
    )
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# FEATURE FLAGS - Enable/disable advanced features
# ============================================================

@dataclass
class PipelineConfig:
    """Configuration for the enhanced pipeline."""
    
    # Adaptive RAG settings
    adaptive_rag_enabled: bool = True
    
    # Tracing settings
    tracing_enabled: bool = True
    export_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Load config from environment variables."""
        return cls(
            adaptive_rag_enabled=os.getenv("ADAPTIVE_RAG_ENABLED", "true").lower() == "true",
            tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            export_metrics=os.getenv("EXPORT_METRICS", "true").lower() == "true",
        )


# ============================================================
# ENHANCED PIPELINE
# ============================================================

class EnhancedPipeline:
    """
    Enhanced RAG pipeline with all advanced features.
    
    Pipeline stages:
    1. Query Classification (Adaptive RAG)
    2. Document Retrieval (with appropriate strategy)
    3. Response Generation
    4. Quality Critique (Feedback Loop)
    5. Iterative Refinement (if needed)
    6. Metrics Export
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize enhanced pipeline."""
        self.config = config or PipelineConfig.from_env()
        
        # Lazy load modules (only when needed)
        self._adaptive_rag = None
        self._tracer = None
    
    @property
    def adaptive_rag(self):
        """Get or create AdaptiveRAG instance."""
        if self._adaptive_rag is None and self.config.adaptive_rag_enabled:
            try:
                from app.rag.adaptive_rag import AdaptiveRAG
                self._adaptive_rag = AdaptiveRAG()
            except ImportError:
                logger.warning("AdaptiveRAG not available")
        return self._adaptive_rag
    
    @property
    def tracer(self):
        """Get or create Tracer instance."""
        if self._tracer is None and self.config.tracing_enabled:
            try:
                from app.observability.tracing import Tracer
                self._tracer = Tracer("enhanced_pipeline")
            except ImportError:
                logger.warning("Tracer not available")
        return self._tracer
    
    async def run(
        self,
        query: str,
        user_profile: Dict[str, Any] = None,
        documents: List[Dict[str, Any]] = None,
        generate_fn=None
    ) -> Dict[str, Any]:
        """
        Run the full enhanced pipeline.
        
        Args:
            query: User query
            user_profile: User profile data
            documents: Pre-retrieved documents (optional)
            generate_fn: Function to generate response (async or sync)
            
        Returns:
            Dict with response and metadata
        """
        result = {
            "query": query,
            "response": "",
            "documents": [],
            "metadata": {
                "stages_run": [],
                "quality_score": 0,
                "was_refined": False,
                "retrieval_strategy": "default",
                "support_verified": False
            }
        }
        
        # Start trace if enabled
        trace_id = None
        if self.tracer:
            trace_id = self.tracer.start_trace(
                name="enhanced_pipeline",
                metadata={"query": query[:100], "user_id": user_profile.get("id") if user_profile else None}
            )
        
        try:
            # Stage 1: Query Classification (Adaptive RAG)
            complexity = "moderate"  # default
            retrieval_config = None
            
            if self.adaptive_rag:
                with self._span("classify_complexity"):
                    complexity = self.adaptive_rag.classify_complexity(query)
                    retrieval_config = self.adaptive_rag.get_retrieval_config(complexity)
                    result["metadata"]["stages_run"].append("adaptive_rag")
                    result["metadata"]["retrieval_strategy"] = complexity.value if hasattr(complexity, 'value') else str(complexity)
            
            # Stage 2: Document Retrieval
            if documents is None:
                with self._span("document_retrieval"):
                    # Use adaptive config if available
                    if self.adaptive_rag and retrieval_config:
                        documents = await self._retrieve_with_config(query, retrieval_config)
                    else:
                        documents = await self._default_retrieval(query)
                    
                    result["metadata"]["stages_run"].append("retrieval")
            
            result["documents"] = documents or []
            
            relevant_docs = documents or []

            # Stage 3: Response Generation
            if generate_fn:
                with self._span("response_generation"):
                    # Build context from relevant docs
                    context = self._build_context(relevant_docs)
                    
                    if asyncio.iscoroutinefunction(generate_fn):
                        response = await generate_fn(query, context, user_profile)
                    else:
                        response = generate_fn(query, context, user_profile)
                    
                    result["response"] = response
                    result["metadata"]["stages_run"].append("generation")
            
            # Stage 4: Export Metrics
            if self.tracer and trace_id:
                self.tracer.end_trace(trace_id)
                
                if self.config.export_metrics:
                    result["metadata"]["trace_id"] = trace_id
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            result["metadata"]["error"] = str(e)
            
            if self.tracer and trace_id:
                self.tracer.end_trace(trace_id, success=False, error=str(e))
        
        return result
    
    def _span(self, name: str):
        """Create a traced span (or no-op context if tracing disabled)."""
        if self.tracer:
            return self.tracer.span(name)
        
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext()
    
    async def _retrieve_with_config(
        self,
        query: str,
        config
    ) -> List[Dict[str, Any]]:
        """Retrieve documents using adaptive config."""
        try:
            from app.rag_hybrid import search_documents
            
            results = await asyncio.to_thread(
                search_documents,
                query,
                top_k=config.top_k
            )
            
            return results
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    async def _default_retrieval(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Default document retrieval."""
        try:
            from app.rag_hybrid import search_documents
            
            results = await asyncio.to_thread(
                search_documents,
                query,
                top_k=top_k
            )
            
            return results
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from documents."""
        if not documents:
            return ""
        
        context_parts = []
        for i, doc in enumerate(documents[:5]):
            text = doc.get("text", doc.get("content", ""))[:1500]
            source = doc.get("source", "Unknown")
            context_parts.append(f"[Source {i+1}: {source}]\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all components."""
        metrics = {
            "pipeline_config": {
                "adaptive_rag_enabled": self.config.adaptive_rag_enabled,
                "tracing_enabled": self.config.tracing_enabled,
            }
        }
        
        if self._adaptive_rag:
            metrics["adaptive_rag"] = self._adaptive_rag.get_metrics()
        
        if self._tracer:
            metrics["tracing"] = self._tracer.get_summary()
        
        return metrics


# ============================================================
# SYNC WRAPPER
# ============================================================

class SyncEnhancedPipeline:
    """Synchronous wrapper for EnhancedPipeline."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self._pipeline = EnhancedPipeline(config)
    
    def run(
        self,
        query: str,
        user_profile: Dict[str, Any] = None,
        documents: List[Dict[str, Any]] = None,
        generate_fn=None
    ) -> Dict[str, Any]:
        """Run pipeline synchronously."""
        return asyncio.run(
            self._pipeline.run(query, user_profile, documents, generate_fn)
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        return self._pipeline.get_metrics()


# ============================================================
# INTEGRATION DECORATORS
# ============================================================

def with_enhanced_rag(func):
    """
    Decorator to add enhanced RAG features to a response function.
    
    Usage:
        @with_enhanced_rag
        async def generate_response(query, context, profile):
            return "..."
    """
    async def wrapper(query: str, *args, **kwargs):
        pipeline = EnhancedPipeline()
        
        async def generate_fn(q, ctx, profile):
            return await func(q, ctx, profile, *args, **kwargs)
        
        result = await pipeline.run(
            query=query,
            user_profile=kwargs.get("user_profile"),
            generate_fn=generate_fn
        )
        
        return result
    
    return wrapper


# ============================================================
# FACTORY FUNCTION
# ============================================================

_pipeline_instance: Optional[EnhancedPipeline] = None


def get_enhanced_pipeline() -> EnhancedPipeline:
    """Get or create global enhanced pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = EnhancedPipeline()
    return _pipeline_instance


def reset_pipeline():
    """Reset the global pipeline instance."""
    global _pipeline_instance
    _pipeline_instance = None
