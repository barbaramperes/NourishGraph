"""
Model Factory for LLM Benchmark

Creates ChatOpenAI-compatible LLM instances for different providers via Azure AI Foundry.
Supports: OpenAI (GPT-4o-mini, GPT-4.1, GPT-5), Anthropic (Claude Sonnet 4.5), DeepSeek-V3.

Usage:
    from model_factory import create_llm, MODELS
    llm = create_llm("gpt-4o-mini")
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from langchain_openai import ChatOpenAI, AzureChatOpenAI


@dataclass
class ModelConfig:
    """Configuration for a benchmark model."""
    name: str                    # Display name
    provider: str                # openai | anthropic | deepseek
    tier: str                    # budget | mid | mid-high | flagship | open-source
    # Pricing per 1M tokens
    input_price: float           # $ per 1M input tokens
    output_price: float          # $ per 1M output tokens
    # Azure deployment info
    deployment_name: str         # Azure deployment name or model name
    azure_endpoint: Optional[str] = None   # Azure endpoint URL (for non-OpenAI models)
    api_key_env: str = "OPENAI_API_KEY"    # Env var holding the API key
    api_version: str = "2024-12-01-preview"


# ============================================================
# MODEL REGISTRY
# ============================================================

MODELS: Dict[str, ModelConfig] = {
    "gpt-4o-mini": ModelConfig(
        name="GPT-4o-mini",
        provider="OpenAI",
        tier="Budget",
        input_price=0.15,
        output_price=0.60,
        deployment_name="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-4.1": ModelConfig(
        name="GPT-4.1",
        provider="OpenAI",
        tier="Mid",
        input_price=2.00,
        output_price=8.00,
        deployment_name="gpt-4.1",
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-5": ModelConfig(
        name="GPT-5",
        provider="OpenAI",
        tier="Flagship",
        input_price=10.00,
        output_price=40.00,
        deployment_name="gpt-5",
        api_key_env="OPENAI_API_KEY",
    ),
    "claude-sonnet-4.5": ModelConfig(
        name="Claude Sonnet 4.5",
        provider="Anthropic",
        tier="Mid-High",
        input_price=3.00,
        output_price=15.00,
        deployment_name="claude-sonnet-4-5-20250514",
        azure_endpoint=os.getenv("AZURE_CLAUDE_ENDPOINT"),
        api_key_env="AZURE_CLAUDE_API_KEY",
        api_version="2024-12-01-preview",
    ),
    "deepseek-v3": ModelConfig(
        name="DeepSeek-V3",
        provider="DeepSeek",
        tier="Open-source",
        input_price=0.27,
        output_price=1.10,
        deployment_name="DeepSeek-V3",
        azure_endpoint=os.getenv("AZURE_DEEPSEEK_ENDPOINT"),
        api_key_env="AZURE_DEEPSEEK_API_KEY",
        api_version="2024-12-01-preview",
    ),
}


def create_llm(
    model_id: str,
    temperature: float = 0.3,
    timeout: int = 90,
    max_retries: int = 2,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """
    Create a ChatOpenAI-compatible LLM instance for the given model.
    
    For OpenAI models: uses standard ChatOpenAI with OPENAI_API_KEY.
    For Azure-hosted non-OpenAI models: uses ChatOpenAI with custom base_url + api_key.
    
    Args:
        model_id: Key from MODELS dict (e.g., "gpt-4o-mini")
        temperature: LLM temperature
        timeout: Request timeout in seconds
        max_retries: Number of retries on failure
        max_tokens: Max output tokens (None = model default)
    
    Returns:
        ChatOpenAI instance
    """
    if model_id not in MODELS:
        raise ValueError(f"Unknown model: {model_id}. Available: {list(MODELS.keys())}")
    
    config = MODELS[model_id]
    api_key = os.getenv(config.api_key_env)
    
    if not api_key:
        raise ValueError(
            f"API key not found. Set {config.api_key_env} environment variable.\n"
            f"Model: {config.name} ({config.provider})"
        )
    
    kwargs = {
        "temperature": temperature,
        "request_timeout": timeout,
        "max_retries": max_retries,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    
    if config.azure_endpoint:
        # Non-OpenAI model via Azure AI Foundry (OpenAI-compatible API)
        return ChatOpenAI(
            model=config.deployment_name,
            api_key=api_key,
            base_url=f"{config.azure_endpoint.rstrip('/')}/v1",
            **kwargs,
        )
    else:
        # Standard OpenAI model
        return ChatOpenAI(
            model=config.deployment_name,
            api_key=api_key,
            **kwargs,
        )


def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token usage."""
    config = MODELS[model_id]
    input_cost = (input_tokens / 1_000_000) * config.input_price
    output_cost = (output_tokens / 1_000_000) * config.output_price
    return input_cost + output_cost


def list_models() -> None:
    """Print available models with pricing."""
    print(f"\n{'Model':<22} {'Provider':<12} {'Tier':<14} {'Input $/1M':<12} {'Output $/1M':<12}")
    print("-" * 72)
    for model_id, cfg in MODELS.items():
        print(f"{cfg.name:<22} {cfg.provider:<12} {cfg.tier:<14} ${cfg.input_price:<11.2f} ${cfg.output_price:<11.2f}")
    print()


if __name__ == "__main__":
    list_models()
