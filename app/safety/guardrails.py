"""
NourishGraph Guardrails System

Healthcare-specific safety guardrails for the nutrition AI assistant.
Based on: Thurzo (2025), Menezes et al. (2025), Gorenshtein et al. (2025)

Features:
- Input validation and risk classification
- Red flag detection (eating disorders, medical emergencies)
- Output filtering with automatic disclaimers
- Escalation protocols for high-risk situations
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime


# ============================================================
# SAFETY LEVELS AND RESULTS
# ============================================================

class SafetyLevel(Enum):
    """Safety classification levels."""
    SAFE = "safe"                    # Normal nutrition query
    CAUTION = "caution"              # Needs disclaimer
    WARNING = "warning"              # Potential risk, add strong disclaimer
    CRITICAL = "critical"            # Medical emergency, refuse and redirect
    BLOCKED = "blocked"              # Harmful content, block completely


@dataclass
class SafetyResult:
    """Result of safety check."""
    level: SafetyLevel
    is_safe: bool
    flags: List[str] = field(default_factory=list)
    message: Optional[str] = None
    requires_disclaimer: bool = False
    requires_escalation: bool = False
    redirect_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "is_safe": self.is_safe,
            "flags": self.flags,
            "message": self.message,
            "requires_disclaimer": self.requires_disclaimer,
            "requires_escalation": self.requires_escalation,
            "redirect_message": self.redirect_message,
        }


# ============================================================
# RED FLAG PATTERNS (Evidence-based)
# ============================================================

# Eating disorder indicators (DSM-5 criteria based)

# Nutrition/research contexts where "fasting" is legitimate (not eating disorder)
_FASTING_SAFE_CONTEXT = re.compile(
    r'(intermittent|time.restricted|research|studies?|evidence|literature|benefits?|metaboli|'
    r'what does|what do|is there|according to|effect of|effects? of)\b.*\bfast',
    re.IGNORECASE,
)

EATING_DISORDER_PATTERNS = [
    # Anorexia indicators — "fasting" handled separately below with context check
    (r'\b(starv|not eat|skip meal|restrict|purge|binge)\w*\b', 'eating_restriction'),
    (r'\bfasting\b', 'fasting_raw'),  # Will be context-checked at runtime
    (r'\b(too fat|so fat|feel fat|look fat|hate my body)\b', 'body_dysmorphia'),
    (r'\b(throw up|vomit|purge|laxative)\w*\s*(after|food|eat)', 'purging_behavior'),
    (r'\b(500|400|300|200)\s*calor\w*\s*(a day|per day|daily|total|diet|only|max)', 'extreme_restriction'),  # Very low daily calorie goals
    (r'\beat\s*(only|just)\s*(500|400|300|200)\s*calor', 'extreme_restriction'),  # "eat only 300 calories"
    (r'\b(anorexi|bulimi|binge eat|eating disorder)\w*\b', 'ed_mention'),
    
    # Obsessive behaviors
    (r'\b(obsess|addict|cant stop|always think)\w*\s*(food|eat|weight|calor)', 'obsessive_food'),
    (r'\b(weigh myself|check weight)\s*(every day|constantly|all the time)', 'obsessive_weighing'),
    
    # Extreme weight loss goals
    (r'lose\s*(\d+)\s*(kg|lb|pound)', 'weight_loss_goal'),  # Will check if extreme
    
    # Rapid weight loss (dangerous timeframes)
    (r'lose\s*\d+\s*(kg|lb|pound)?\s*(in|within)?\s*(one|1|a)\s*(week|day)', 'rapid_weight_loss'),
    (r'(one|1|a)\s*(week|day)\s*(lose|drop|shed)\s*\d+', 'rapid_weight_loss'),
    (r'(fast|quick|rapid)\s*(weight loss|lose weight|drop weight)', 'rapid_weight_loss'),
]

# Medical emergency indicators
MEDICAL_EMERGENCY_PATTERNS = [
    (r'\b(chest pain|heart attack|stroke|seizure|faint|collapse)\w*\b', 'emergency'),
    (r'\b(cant breathe|difficulty breath|short of breath)\b', 'respiratory'),
    (r'\b(severe pain|intense pain|unbearable pain)\b', 'severe_pain'),
    (r'\b(blood sugar|hypoglycemia|hyperglycemia)\s*(very|extremely|dangerously)', 'glucose_emergency'),
    (r'\b(allergic reaction|anaphyla|swelling|hives)\w*\b', 'allergic_reaction'),
    (r'\b(suicid|kill myself|end my life|dont want to live)\w*\b', 'mental_health_crisis'),
]

# Medical condition indicators (need disclaimer)
MEDICAL_CONDITION_PATTERNS = [
    (r'\b(diabetes|diabetic)\w*\b', 'diabetes'),
    (r'\b(heart disease|cardiovascular|hypertension|high blood pressure)\w*\b', 'cardiovascular'),
    (r'\b(kidney|renal)\s*(disease|failure|problem)\w*\b', 'renal'),
    (r'\b(liver|hepat)\s*(disease|failure|problem)\w*\b', 'hepatic'),
    (r'\b(cancer|tumor|oncolog)\w*\b', 'oncology'),
    (r'\b(pregnan|expecting|baby)\w*\b', 'pregnancy'),
    (r'\b(breastfeed|nursing|lactating)\w*\b', 'lactation'),
    (r'\b(celiac|gluten intoleran|crohn|ibs|ibd)\w*\b', 'gi_condition'),
    (r'\b(thyroid|hypothyroid|hyperthyroid)\w*\b', 'thyroid'),
    (r'\b(pcos|polycystic)\w*\b', 'hormonal'),
    (r'\b(headache|migraine|frequent headache|chronic headache)\w*\b', 'symptom'),
]

# Medication interactions
MEDICATION_PATTERNS = [
    (r'\b(medication|medicine|drug|prescription|pill)\w*\b', 'medication_general'),
    (r'\b(warfarin|coumadin|blood thinner)\w*\b', 'anticoagulant'),
    (r'\b(insulin|metformin|glipizide)\w*\b', 'diabetes_med'),
    (r'\b(statin|lipitor|cholesterol)\w*\b', 'cholesterol_med'),
    (r'\b(antidepressant|ssri|maoi)\w*\b', 'psychiatric_med'),
]

# Supplement safety concerns
SUPPLEMENT_PATTERNS = [
    (r'\b(supplement|vitamin|mineral)\s*(megados|high dos|large dos)', 'megadose'),
    (r'\b(detox|cleanse|flush)\w*\b', 'detox_claim'),
    (r'\b(fat burner|thermogenic|metabolism boost)\w*\b', 'weight_loss_supplement'),
    (r'\b(take|should i take|need)\s*(vitamin|supplement|mineral|magnesium|zinc|iron|calcium|omega|probiotic|melatonin|creatine|collagen)\w*\b', 'supplement_advice'),
    (r'\b(vitamin|supplement)\s*(for|to help|to treat|to cure)\b', 'supplement_advice'),
    # Only match "vitamin D supplement/pill/tablet" — require the supplement word, not optional
    (r'\bvitamin\s+(a|b|b6|b12|c|d|d3|e|k|k2)\s+(supplement|pill|tablet|capsule)\w*\b', 'supplement_advice'),
    (r'\b(magnesium|zinc|iron|calcium|omega|probiotic|melatonin|creatine|collagen)\s*(for|to help|to treat|to cure)\b', 'supplement_advice'),
    # Supplements for symptoms (user wants to treat a symptom with supplements)
    (r'\b(supplement|vitamin|mineral|magnesium|zinc|iron|calcium|omega|probiotic|melatonin)\w*\s*.{0,20}\b(headache|migraine|pain|fatigue|tired|insomnia|anxiety|depression|nausea|dizz)\w*\b', 'supplement_for_symptom'),
    (r'\b(headache|migraine|pain|fatigue|tired|insomnia|anxiety|depression|nausea|dizz)\w*\s*.{0,20}\b(supplement|vitamin|mineral|magnesium|zinc|iron|calcium|omega|probiotic|melatonin)\w*\b', 'supplement_for_symptom'),
]


# ============================================================
# INPUT GUARD
# ============================================================

class InputGuard:
    """
    Validates and classifies user input for safety.
    
    Based on: Thurzo (2025) - Healthcare AI safety frameworks
    """
    
    def __init__(self):
        self.patterns = {
            'eating_disorder': EATING_DISORDER_PATTERNS,
            'medical_emergency': MEDICAL_EMERGENCY_PATTERNS,
            'medical_condition': MEDICAL_CONDITION_PATTERNS,
            'medication': MEDICATION_PATTERNS,
            'supplement': SUPPLEMENT_PATTERNS,
        }
    
    # Queries asking about research/science should not trigger supplement safety
    SCIENCE_QUERY_PATTERN = re.compile(
        r'\b(research|study|studies|evidence|scientific|science|literature|review|meta.?analysis)\b'
        r'.{0,40}'
        r'\b(say|show|suggest|find|found|report|indicate|demonstrate|reveal|about|between|effect|benefit|role|relationship|impact)\b',
        re.IGNORECASE
    )
    
    def check(self, text: str) -> SafetyResult:
        """
        Check input text for safety concerns.
        
        Returns SafetyResult with classification and flags.
        """
        text_lower = text.lower()
        flags = []
        
        # Detect if this is a pure science/research question
        is_science_query = bool(self.SCIENCE_QUERY_PATTERN.search(text_lower))
        
        # Check for medical emergencies (CRITICAL)
        for pattern, flag in MEDICAL_EMERGENCY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flags.append(f"emergency:{flag}")
        
        if any('emergency:' in f for f in flags):
            return SafetyResult(
                level=SafetyLevel.CRITICAL,
                is_safe=False,
                flags=flags,
                message="Medical emergency detected",
                requires_escalation=True,
                redirect_message=self._get_emergency_message(flags)
            )
        
        # Check for eating disorder indicators (WARNING)
        ed_flags = []
        for pattern, flag in EATING_DISORDER_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # "fasting" needs context check — skip in nutrition/research contexts
                if flag == 'fasting_raw':
                    if _FASTING_SAFE_CONTEXT.search(text_lower):
                        continue  # Legitimate nutrition question, not ED
                    ed_flags.append("eating_disorder:eating_restriction")
                # Special check for weight loss goals
                elif flag == 'weight_loss_goal':
                    try:
                        amount = int(match.group(1))
                        if amount > 20:  # More than 20 kg/lb is extreme
                            ed_flags.append(f"eating_disorder:extreme_weight_goal_{amount}")
                    except:
                        pass
                else:
                    ed_flags.append(f"eating_disorder:{flag}")
        
        if ed_flags:
            flags.extend(ed_flags)
            return SafetyResult(
                level=SafetyLevel.WARNING,
                is_safe=True,  # Allow but with strong disclaimer
                flags=flags,
                message="Potential eating disorder indicators detected",
                requires_disclaimer=True,
                requires_escalation=len(ed_flags) >= 2,  # Multiple flags = higher concern
                redirect_message=self._get_ed_support_message() if len(ed_flags) >= 2 else None
            )
        
        # Check for medical conditions (CAUTION)
        condition_flags = []
        for pattern, flag in MEDICAL_CONDITION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                condition_flags.append(f"medical:{flag}")
        
        # Check for medication mentions (CAUTION)
        for pattern, flag in MEDICATION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                condition_flags.append(f"medication:{flag}")
        
        # Check for supplement concerns (CAUTION)
        # Skip supplement patterns for pure science/research queries
        supplement_flags = []
        if not is_science_query:
            for pattern, flag in SUPPLEMENT_PATTERNS:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    supplement_flags.append(f"supplement:{flag}")
        
        # Combine all caution-level flags and return together
        all_caution_flags = condition_flags + supplement_flags
        if all_caution_flags:
            flags.extend(all_caution_flags)
            return SafetyResult(
                level=SafetyLevel.CAUTION,
                is_safe=True,
                flags=flags,
                message="Medical condition, medication, or supplement concern detected",
                requires_disclaimer=True
            )
        
        # Default: SAFE
        return SafetyResult(
            level=SafetyLevel.SAFE,
            is_safe=True,
            flags=[]
        )
    
    def _get_emergency_message(self, flags: List[str]) -> str:
        """Generate emergency redirect message."""
        if any('mental_health' in f for f in flags):
            return (
                "⚠️ **I'm concerned about what you've shared.**\n\n"
                "If you're having thoughts of suicide or self-harm, please reach out for help:\n\n"
                "🆘 **Emergency**: Call 112 (EU) or your local emergency number\n"
                "📞 **Crisis Line**: Contact a mental health crisis line in your country\n"
                "💬 **Talk to someone**: Reach out to a trusted friend, family member, or mental health professional\n\n"
                "You are not alone, and help is available. ❤️"
            )
        
        return (
            "⚠️ **This sounds like a medical emergency.**\n\n"
            "I'm an AI nutrition assistant and cannot provide emergency medical advice.\n\n"
            "🆘 **Please seek immediate medical help:**\n"
            "• Call emergency services: 112 (EU) or your local emergency number\n"
            "• Go to the nearest emergency room\n"
            "• Contact your doctor immediately\n\n"
            "Your health and safety are the priority."
        )
    
    def _get_ed_support_message(self) -> str:
        """Generate eating disorder support message."""
        return (
            "💙 **I notice some concerning patterns in what you've shared.**\n\n"
            "If you're struggling with your relationship with food or body image, "
            "you're not alone and support is available:\n\n"
            "• **Talk to a professional**: A registered dietitian or therapist specializing in eating disorders can help\n"
            "• **Helplines**: Contact an eating disorder support organization in your country\n"
            "• **Be kind to yourself**: Recovery is possible, and seeking help is a sign of strength\n\n"
            "I'm here to support healthy nutrition, but some concerns are best addressed with professional help. ❤️"
        )


# ============================================================
# OUTPUT GUARD
# ============================================================

class OutputGuard:
    """
    Filters AI responses and adds appropriate disclaimers.
    
    Based on: Gorenshtein et al. (2025) - Medical AI disclaimers
    """
    
    # Standard disclaimers by context
    DISCLAIMERS = {
        'general': (
            "\n\n---\n"
            "ℹ️ *This information is for educational purposes only and is not a substitute "
            "for professional medical or nutritional advice.*"
        ),
        'medical_condition': (
            "\n\n---\n"
            "⚠️ *Given your health condition, please consult with your healthcare provider "
            "or a registered dietitian before making dietary changes.*"
        ),
        'medication': (
            "\n\n---\n"
            "💊 *Some foods can interact with medications. Please consult your doctor or "
            "pharmacist about potential food-drug interactions.*"
        ),
        'weight_loss': (
            "\n\n---\n"
            "📊 *Sustainable weight management involves balanced nutrition, regular physical activity, "
            "and behavioral changes. Consider working with a healthcare professional for personalized guidance.*"
        ),
        'pregnancy': (
            "\n\n---\n"
            "🤰 *Nutritional needs during pregnancy are unique. Please work with your "
            "healthcare provider or a prenatal dietitian for personalized recommendations.*"
        ),
        'supplement': (
            "\n\n---\n"
            "💊 *Supplements should complement, not replace, a balanced diet. Consult a healthcare "
            "provider before starting any supplement regimen.*"
        ),
    }
    
    def filter(self, response: str, safety_result: SafetyResult) -> str:
        """
        Filter response and add appropriate disclaimers.
        Only add disclaimers when there are specific safety flags.
        """
        if not safety_result.requires_disclaimer:
            # Don't add general disclaimers to all responses
            # Only add if there's actual advice AND weight loss discussion
            if self._contains_weight_advice(response):
                return response + self.DISCLAIMERS['general']
            return response
        
        # Add context-specific disclaimer only for specific flags
        disclaimer = self._select_disclaimer(safety_result.flags)
        return response + disclaimer
    
    def _contains_weight_advice(self, text: str) -> bool:
        """Check if response contains specific weight loss/gain advice."""
        text_lower = text.lower()
        # Only trigger for weight-related advice, not all nutrition mentions
        weight_terms = ['weight loss', 'lose weight', 'weight gain', 'gain weight', 'diet plan', 'calorie deficit']
        advice_terms = ['should', 'recommend', 'suggest']
        has_weight = any(term in text_lower for term in weight_terms)
        has_advice = any(term in text_lower for term in advice_terms)
        return has_weight and has_advice
    
    def _contains_advice(self, text: str) -> bool:
        """Check if response contains nutritional advice."""
        advice_indicators = [
            'should', 'recommend', 'suggest', 'try', 'consider',
            'eat', 'avoid', 'include', 'limit', 'increase', 'decrease',
            'calories', 'protein', 'carbs', 'fat', 'nutrient',
            'meal', 'diet', 'food'
        ]
        text_lower = text.lower()
        return any(ind in text_lower for ind in advice_indicators)
    
    def _select_disclaimer(self, flags: List[str]) -> str:
        """Select most appropriate disclaimer based on flags.
        
        Note: For supplement and medication flags, the frontend already shows
        a SafetyMessage component, so we don't add text disclaimers to avoid
        redundancy.
        """
        # Priority order - eating_disorder flags are now ignored (no disclaimer)
        if any('eating_disorder' in f for f in flags):
            return ""  # No special disclaimer for this
        if any('pregnancy' in f or 'lactation' in f for f in flags):
            return self.DISCLAIMERS['pregnancy']
        # Supplement and medication disclaimers are handled by frontend SafetyMessage
        if any('medication' in f for f in flags):
            return ""  # Frontend shows SafetyMessage for medication
        if any('supplement' in f for f in flags):
            return ""  # Frontend shows SafetyMessage for supplements
        if any('medical:' in f for f in flags):
            return self.DISCLAIMERS['medical_condition']
        
        return self.DISCLAIMERS['general']


# ============================================================
# RED FLAG DETECTOR
# ============================================================

class RedFlagDetector:
    """
    Detects red flags that require immediate attention or escalation.
    
    Based on: Clinical guidelines for eating disorder screening
    """
    
    # SCOFF questionnaire indicators (validated screening tool)
    SCOFF_PATTERNS = [
        r'make yourself sick',
        r'lost control.*eating',
        r'lost.*\d+.*pounds|kg.*recently',
        r'believe.*fat.*others.*thin',
        r'food dominates.*life',
    ]
    
    def __init__(self):
        self.input_guard = InputGuard()
    
    def detect(self, text: str, user_history: Optional[List[str]] = None) -> SafetyResult:
        """
        Comprehensive red flag detection.
        
        Checks current input and optionally user history for patterns.
        """
        # Check current input
        result = self.input_guard.check(text)
        
        # If we have history, look for patterns
        if user_history and len(user_history) >= 3:
            pattern_flags = self._check_history_patterns(user_history)
            if pattern_flags:
                result.flags.extend(pattern_flags)
                if len(pattern_flags) >= 2:
                    result.level = SafetyLevel.WARNING
                    result.requires_escalation = True
        
        return result
    
    def _check_history_patterns(self, history: List[str]) -> List[str]:
        """Check conversation history for concerning patterns."""
        flags = []
        combined_text = ' '.join(history).lower()
        
        # Check for repeated weight/calorie obsession
        weight_mentions = len(re.findall(r'\b(weight|weigh|scale|kg|lb|pound)\b', combined_text))
        calorie_mentions = len(re.findall(r'\b(calori|kcal)\w*\b', combined_text))
        
        if weight_mentions > 5:
            flags.append('pattern:weight_obsession')
        if calorie_mentions > 10:
            flags.append('pattern:calorie_obsession')
        
        # Check for SCOFF-like patterns
        scoff_count = 0
        for pattern in self.SCOFF_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                scoff_count += 1
        
        if scoff_count >= 2:
            flags.append('pattern:scoff_positive')
        
        return flags


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

# Singleton instances
_input_guard = InputGuard()
_output_guard = OutputGuard()
_red_flag_detector = RedFlagDetector()


def check_input_safety(text: str) -> SafetyResult:
    """Check input text for safety concerns."""
    return _input_guard.check(text)


def add_safety_disclaimer(response: str, safety_result: SafetyResult) -> str:
    """Add appropriate safety disclaimer to response."""
    return _output_guard.filter(response, safety_result)


def detect_red_flags(text: str, history: Optional[List[str]] = None) -> SafetyResult:
    """Comprehensive red flag detection."""
    return _red_flag_detector.detect(text, history)
