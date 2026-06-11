"""
Intent Classifier for NourishGraph
Classifies user queries into appropriate agent categories.
Includes safety detection for medical queries - BLOCKS medication dosage queries.
"""

from typing import Dict, List


class IntentClassifier:
    """Classifies user intent based on query content."""
    
    def __init__(self):
        # Keywords por intent - ordem de prioridade
        self.patterns = {
            "meal_planner": [
                "suggest", "plan", "make me", "create", "prepare",
                "breakfast", "lunch", "dinner", "snack", "meal",
                "recipe", "cook", "eat for", "food idea", "what to eat"
            ],
            "science": [
                "research", "study", "studies", "evidence", "scientific",
                "journal", "paper", "literature", "review", "findings",
                "published", "according to"
            ],
            "profile": [
                "update", "change", "set", "my goal", "allergic",
                "preference", "weight to", "level to", "i weigh",
                "my age", "intolerant", "i am", "years old"
            ],
            "nutrition": [
                "calorie", "protein", "carb", "fat", "macro",
                "bmr", "tdee", "water", "intake", "nutrient",
                "vitamin", "mineral", "requirement", "how much", "daily"
            ],
            "chat": [
                "hello", "hi", "thanks", "thank you", "bye", "help",
                "good morning", "good evening", "what can you do"
            ]
        }
        
        # CRITICAL: Medical keywords that MUST trigger blocking
        # Checked BEFORE any other classification
        self.medical_block_keywords = [
            # Insulin and diabetes medications
            "insulin", "metformin", "glipizide", "glyburide", "ozempic",
            "trulicity", "victoza", "jardiance", "invokana",
            
            # Dosage terms - CRITICAL
            "dosage", "dose", "doses", "mg", "milligram", "units",
            "how much to take", "how many to take", "correct dose",
            "right dose", "proper dose", "recommended dose",
            
            # Medication management
            "medication", "medicine", "drug", "prescription", "pill",
            "tablet", "capsule", "injection", "inject", "syringe",
            
            # Medical actions
            "diagnose", "diagnosis", "treatment", "cure", "surgery",
            
            # Changing medication
            "stop taking", "stop my", "quit taking", "discontinue",
            "reduce my", "increase my", "double my", "skip my",
            
            # Blood markers requiring medical supervision
            "blood pressure", "blood sugar", "blood glucose", "a1c",
            "cholesterol level",
            
            # Drug interactions
            "can i take", "safe to take", "mix with", "combine with",
            
            # Other medications
            "aspirin", "ibuprofen", "warfarin", "blood thinner",
            "antidepressant", "antibiotic", "painkiller", "opioid",
            
            # Emergency terms
            "overdose", "poisoning", "emergency", "chest pain",
            
            # Special populations
            "pediatric", "child dose", "pregnant", "breastfeeding"
        ]
        
        # Phrases that ALWAYS indicate medical intent
        self.medical_block_phrases = [
            "correct dosage", "right dosage", "proper dosage",
            "how much insulin", "insulin dose", "insulin dosage",
            "for my weight", "based on my weight",
            "should i take", "should i stop", "should i reduce",
            "can i stop", "can i reduce", "can i increase",
            "what dosage", "what dose", "how many mg",
            "is it safe to take", "safe to mix"
        ]
    
    def classify(self, query: str) -> Dict:
        """
        Classify user query into an intent category.
        ALWAYS checks for medical content FIRST - blocks before any other processing.
        """
        query_lower = query.lower()
        
        # STEP 1: Check for medical content FIRST - CRITICAL SAFETY CHECK
        is_medical, reason = self._is_medical_query(query_lower)
        
        if is_medical:
            return {
                "intent": "medical_blocked",  # Special intent for blocked queries
                "confidence": 1.0,
                "is_medical": True,
                "blocked": True,
                "block_reason": reason,
                "query": query
            }
        
        # STEP 2: Normal classification only if NOT medical
        intent = self._determine_intent(query_lower)
        confidence = self._calculate_confidence(query_lower, intent)
        
        return {
            "intent": intent,
            "confidence": confidence,
            "is_medical": False,
            "blocked": False,
            "query": query
        }
    
    def _is_medical_query(self, query_lower: str) -> tuple:
        """
        Check if query contains medical content that should be blocked.
        Returns (is_medical: bool, reason: str)
        """
        # Check phrases first (more specific)
        for phrase in self.medical_block_phrases:
            if phrase in query_lower:
                return True, f"medical_phrase:{phrase}"
        
        # Check individual keywords
        for keyword in self.medical_block_keywords:
            if keyword in query_lower:
                return True, f"medical_keyword:{keyword}"
        
        # Special combination checks
        # "insulin" + anything about dosage/amount
        if "insulin" in query_lower:
            dosage_terms = ["dosage", "dose", "how much", "correct", "right", "units", "mg"]
            if any(term in query_lower for term in dosage_terms):
                return True, "insulin_dosage_query"
        
        # "metformin" + dosage
        if "metformin" in query_lower:
            if any(term in query_lower for term in ["dose", "dosage", "reduce", "stop"]):
                return True, "metformin_dosage_query"
        
        return False, ""
    
    def _determine_intent(self, query_lower: str) -> str:
        """Determine the intent based on keyword matching with priority handling."""
        
        # PRIORITY 1: Meal planning keywords take precedence
        # This prevents "I am vegetarian" from being classified as profile update
        # when the user is actually asking for meal suggestions
        meal_keywords = self.patterns.get("meal_planner", [])
        meal_strong_keywords = ["suggest", "breakfast", "lunch", "dinner", "snack", 
                                 "recipe", "meal plan", "what to eat", "food idea"]
        
        if any(kw in query_lower for kw in meal_strong_keywords):
            return "meal_planner"
        
        # PRIORITY 2: Profile updates only when explicitly requested
        # Keywords like "update", "change", "set" indicate explicit profile intent
        profile_explicit_keywords = ["update my", "change my", "set my", "save my",
                                      "my weight is", "my age is", "my height is"]
        if any(kw in query_lower for kw in profile_explicit_keywords):
            return "profile"
        
        # PRIORITY 3: Science queries when research-related terms are present
        science_keywords = self.patterns.get("science", [])
        if any(kw in query_lower for kw in science_keywords):
            return "science"
        
        # PRIORITY 4: Nutrition calculations
        nutrition_keywords = self.patterns.get("nutrition", [])
        if any(kw in query_lower for kw in nutrition_keywords):
            return "nutrition"
        
        # PRIORITY 5: General meal planning (broader match)
        if any(kw in query_lower for kw in meal_keywords):
            return "meal_planner"
        
        # PRIORITY 6: Profile (only if no meal context)
        # Exclude "allergic" and "vegetarian" etc. when food context is present
        food_context = any(word in query_lower for word in 
                          ["eat", "food", "meal", "breakfast", "lunch", "dinner"])
        if not food_context:
            profile_keywords = self.patterns.get("profile", [])
            if any(kw in query_lower for kw in profile_keywords):
                return "profile"
        
        # DEFAULT: Chat agent
        return "chat"
    
    def _calculate_confidence(self, query_lower: str, intent: str) -> float:
        """Calculate confidence score based on keyword matches."""
        if intent not in self.patterns:
            return 0.5
        
        keywords = self.patterns[intent]
        matches = sum(1 for kw in keywords if kw in query_lower)
        
        if matches >= 3:
            return 0.95
        elif matches >= 2:
            return 0.85
        elif matches >= 1:
            return 0.75
        return 0.5
