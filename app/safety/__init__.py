"""
NourishGraph Safety Module

Implements healthcare-specific guardrails based on literature:
- Thurzo (2025): Patient safety in AI healthcare
- Menezes et al. (2025): Safety-critical AI systems
- Gorenshtein et al. (2025): Medical AI disclaimers

Components:
1. InputGuard - Validates and classifies user input
2. OutputGuard - Filters and adds disclaimers to responses
3. RedFlagDetector - Detects eating disorders, medical emergencies
4. SafetyMetrics - Tracks safety compliance
"""

from .guardrails import (
    InputGuard,
    OutputGuard,
    RedFlagDetector,
    SafetyLevel,
    SafetyResult,
    check_input_safety,
    add_safety_disclaimer,
    detect_red_flags,
)

from .metrics import SafetyMetrics

__all__ = [
    "InputGuard",
    "OutputGuard", 
    "RedFlagDetector",
    "SafetyLevel",
    "SafetyResult",
    "SafetyMetrics",
    "check_input_safety",
    "add_safety_disclaimer",
    "detect_red_flags",
]
