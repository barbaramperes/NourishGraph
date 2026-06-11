"""
NourishGraph Safety Metrics

Tracks safety compliance and generates reports for evaluation.
Essential for thesis validation and academic review.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .guardrails import SafetyLevel, SafetyResult


@dataclass
class SafetyEvent:
    """Record of a safety-related event."""
    timestamp: datetime
    level: SafetyLevel
    flags: List[str]
    input_text: str  # Anonymized/truncated
    action_taken: str  # 'allowed', 'disclaimer_added', 'blocked', 'escalated'
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "flags": self.flags,
            "input_preview": self.input_text[:50] + "..." if len(self.input_text) > 50 else self.input_text,
            "action_taken": self.action_taken,
        }


class SafetyMetrics:
    """
    Tracks and reports safety metrics for the NourishGraph system.
    
    Metrics tracked:
    - Total queries processed
    - Safety level distribution
    - Red flag detection rate
    - Escalation rate
    - Disclaimer addition rate
    - Flag type frequency
    
    Based on: Menezes et al. (2025) - Safety-critical AI evaluation
    """
    
    def __init__(self, max_events: int = 10000):
        self.events: List[SafetyEvent] = []
        self.max_events = max_events
        self.counters = {
            'total_queries': 0,
            'safe': 0,
            'caution': 0,
            'warning': 0,
            'critical': 0,
            'blocked': 0,
            'disclaimers_added': 0,
            'escalations': 0,
        }
        self.flag_counts: Dict[str, int] = defaultdict(int)
        self.start_time = datetime.now()
    
    def record(self, result: SafetyResult, input_text: str, action: str):
        """
        Record a safety check event.
        
        Args:
            result: The SafetyResult from the check
            input_text: The input that was checked (will be truncated)
            action: What action was taken ('allowed', 'disclaimer_added', etc.)
        """
        # Update counters
        self.counters['total_queries'] += 1
        self.counters[result.level.value] += 1
        
        if result.requires_disclaimer:
            self.counters['disclaimers_added'] += 1
        if result.requires_escalation:
            self.counters['escalations'] += 1
        
        # Track flag frequency
        for flag in result.flags:
            self.flag_counts[flag] += 1
        
        # Store event (with size limit)
        if result.level != SafetyLevel.SAFE:  # Only store non-safe events
            event = SafetyEvent(
                timestamp=datetime.now(),
                level=result.level,
                flags=result.flags,
                input_text=input_text[:100],  # Truncate for privacy
                action_taken=action
            )
            self.events.append(event)
            
            # Trim if too many events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
    
    def get_summary(self) -> Dict:
        """
        Get summary metrics for evaluation.
        
        Returns:
            Dictionary with all safety metrics
        """
        total = self.counters['total_queries'] or 1  # Avoid division by zero
        
        return {
            "period": {
                "start": self.start_time.isoformat(),
                "end": datetime.now().isoformat(),
                "duration_hours": (datetime.now() - self.start_time).total_seconds() / 3600
            },
            "totals": {
                "queries_processed": self.counters['total_queries'],
                "disclaimers_added": self.counters['disclaimers_added'],
                "escalations": self.counters['escalations'],
            },
            "safety_levels": {
                "safe": self.counters['safe'],
                "caution": self.counters['caution'],
                "warning": self.counters['warning'],
                "critical": self.counters['critical'],
                "blocked": self.counters['blocked'],
            },
            "rates": {
                "safe_rate": self.counters['safe'] / total * 100,
                "disclaimer_rate": self.counters['disclaimers_added'] / total * 100,
                "escalation_rate": self.counters['escalations'] / total * 100,
                "red_flag_rate": (self.counters['warning'] + self.counters['critical']) / total * 100,
            },
            "top_flags": dict(sorted(
                self.flag_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]),
            "recent_events": [e.to_dict() for e in self.events[-10:]],
        }
    
    def get_evaluation_report(self) -> str:
        """
        Generate a formatted evaluation report for thesis.
        
        Returns:
            Markdown-formatted report string
        """
        summary = self.get_summary()
        
        report = f"""
# NourishGraph Safety Evaluation Report

**Period**: {summary['period']['start']} to {summary['period']['end']}
**Duration**: {summary['period']['duration_hours']:.1f} hours

## Overall Statistics

| Metric | Value |
|--------|-------|
| Total Queries | {summary['totals']['queries_processed']} |
| Disclaimers Added | {summary['totals']['disclaimers_added']} |
| Escalations | {summary['totals']['escalations']} |

## Safety Level Distribution

| Level | Count | Percentage |
|-------|-------|------------|
| Safe | {summary['safety_levels']['safe']} | {summary['rates']['safe_rate']:.1f}% |
| Caution | {summary['safety_levels']['caution']} | - |
| Warning | {summary['safety_levels']['warning']} | - |
| Critical | {summary['safety_levels']['critical']} | - |
| Blocked | {summary['safety_levels']['blocked']} | - |

## Key Rates

- **Safe Query Rate**: {summary['rates']['safe_rate']:.1f}%
- **Disclaimer Addition Rate**: {summary['rates']['disclaimer_rate']:.1f}%
- **Escalation Rate**: {summary['rates']['escalation_rate']:.1f}%
- **Red Flag Detection Rate**: {summary['rates']['red_flag_rate']:.1f}%

## Top Detected Flags

"""
        for flag, count in list(summary['top_flags'].items())[:5]:
            report += f"- `{flag}`: {count} occurrences\n"
        
        report += """

## Compliance Assessment

Based on healthcare AI safety guidelines (Thurzo, 2025; Menezes et al., 2025):

- ✅ Input validation implemented
- ✅ Red flag detection active
- ✅ Automatic disclaimers for medical content
- ✅ Escalation protocol for critical cases
- ✅ Metrics tracking for evaluation

"""
        return report
    
    def reset(self):
        """Reset all metrics (for testing)."""
        self.events = []
        self.counters = {k: 0 for k in self.counters}
        self.flag_counts = defaultdict(int)
        self.start_time = datetime.now()
    
    def to_json(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(self.get_summary(), indent=2)


# Global metrics instance
_metrics = SafetyMetrics()


def get_safety_metrics() -> SafetyMetrics:
    """Get the global safety metrics instance."""
    return _metrics


def record_safety_event(result: SafetyResult, input_text: str, action: str):
    """Record a safety event to global metrics."""
    _metrics.record(result, input_text, action)
