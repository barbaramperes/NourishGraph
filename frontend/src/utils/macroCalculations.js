/**
 * Macro Calculations Utility
 * 
 * Evidence-based macronutrient distribution calculator based on diet type, goals,
 * and activity level. References from scientific literature:
 * 
 * REFERENCES:
 * 1. Ketogenic Diet - NCBI PMC8153354: 55-60% fat, 30-35% protein, 5-10% carbs (20-50g/day)
 * 2. Protein Requirements - Examine.com (2023):
 *    - Sedentary: 1.2 g/kg bodyweight
 *    - Muscle gain: 1.6-2.2 g/kg bodyweight
 *    - Fat loss: 1.6-2.4 g/kg bodyweight
 *    - Older adults: 1.2-1.6 g/kg bodyweight
 * 3. Mediterranean Diet - American Heart Association: 45-50% carbs, 20% protein, 30-35% fat
 * 4. Low-Carb Diet - Journal of Clinical Nutrition: 20-30% carbs, 30% protein, 40-50% fat
 * 5. AMDR (Acceptable Macronutrient Distribution Ranges) - USDA Dietary Guidelines:
 *    - Carbs: 45-65%, Protein: 10-35%, Fat: 20-35%
 * 
 * @author NourishGraph Team
 */

/**
 * Activity level multipliers for TDEE calculation
 * Based on Mifflin-St Jeor equation with activity factors
 */
const ACTIVITY_MULTIPLIERS = {
    sedentary: 1.2,      // Little or no exercise
    light: 1.375,        // Light exercise 1-3 days/week
    moderate: 1.55,      // Moderate exercise 3-5 days/week
    active: 1.725,       // Heavy exercise 6-7 days/week
    very_active: 1.9     // Very heavy exercise, physical job
};

/**
 * Calculate calorie goal using Mifflin-St Jeor equation + activity level + goal adjustment
 * This is the SINGLE SOURCE OF TRUTH for calorie calculations across the entire app.
 * 
 * @param {Object} profile - User profile with weight, height, age, gender, activity, goal
 * @returns {number|null} - Daily calorie goal or null if insufficient data
 */
export function calculateCalorieGoal(profile) {
    // If user has manually set a calorie goal, use that
    if (profile?.calorie_goal) return profile.calorie_goal;

    const { weight, height, age, gender, activity = 'moderate', goal = 'maintain' } = profile || {};

    // Need minimum data to calculate
    if (!weight || !height || !age) return null;

    // Mifflin-St Jeor equation for BMR
    // Males: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(y) + 5
    // Females: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age(y) - 161
    const isMale = gender?.toLowerCase?.().startsWith('m');
    const bmr = isMale
        ? 10 * weight + 6.25 * height - 5 * age + 5
        : 10 * weight + 6.25 * height - 5 * age - 161;

    // Apply activity multiplier to get TDEE (don't round yet)
    const multiplier = ACTIVITY_MULTIPLIERS[activity] || ACTIVITY_MULTIPLIERS.moderate;
    const tdee = bmr * multiplier;

    // Apply goal-based adjustment and round at the end
    // Lose weight: -500 kcal/day (safe deficit of ~0.5kg/week)
    // Gain muscle: +300 kcal/day (moderate surplus for lean gain)
    if (goal === 'lose' || goal === 'lose_weight') {
        return Math.round(tdee - 500);
    }
    if (goal === 'gain' || goal === 'gain_muscle') {
        return Math.round(tdee + 300);
    }

    // Maintain weight
    return Math.round(tdee);
}

/**
 * Diet-specific macro percentage distributions
 * Based on evidence from scientific literature
 */
export const DIET_MACRO_DISTRIBUTIONS = {
    // Default balanced diet (USDA Guidelines)
    '': {
        name: 'Balanced',
        carbs: 50,      // 50% of calories from carbs
        protein: 25,    // 25% of calories from protein
        fat: 25,        // 25% of calories from fat
        description: 'USDA Dietary Guidelines (2020-2025)',
        source: 'USDA AMDR Guidelines'
    },

    // Mediterranean Diet (American Heart Association)
    'mediterranean': {
        name: 'Mediterranean',
        carbs: 45,
        protein: 20,
        fat: 35,        // Emphasis on healthy fats (olive oil, nuts, fish)
        description: 'Emphasis on healthy fats from olive oil, nuts, and fish',
        source: 'American Heart Association'
    },

    // Vegetarian (similar to balanced, slightly higher carbs)
    'vegetarian': {
        name: 'Vegetarian',
        carbs: 50,
        protein: 20,    // May need more volume to hit protein
        fat: 30,
        description: 'Plant-based proteins with adequate intake recommended',
        source: 'Academy of Nutrition and Dietetics Position Paper'
    },

    // Vegan (slightly higher carbs, moderate protein)
    'vegan': {
        name: 'Vegan',
        carbs: 55,
        protein: 18,    // Combine protein sources for complete amino acids
        fat: 27,
        description: 'Combine legumes, grains, seeds for complete proteins',
        source: 'Academy of Nutrition and Dietetics Position Paper'
    },

    // Ketogenic Diet (NCBI PMC8153354)
    'keto': {
        name: 'Ketogenic',
        carbs: 5,       // 5-10% (typically 20-50g/day max)
        protein: 30,    // 30-35%
        fat: 65,        // 55-65% (primary fuel source)
        description: 'Very low-carb (20-50g/day) to induce ketosis',
        source: 'NCBI PMC8153354 - Ketogenic Diet Review'
    },

    // Carnivore Diet (animal products only)
    'carnivore': {
        name: 'Carnivore',
        carbs: 0,       // Zero or near-zero carbs
        protein: 35,    // High protein from meat
        fat: 65,        // High fat from animal sources
        description: 'Animal products only - very restrictive',
        source: 'Clinical observations, limited research'
    },

    // Paleo Diet (ancestral eating pattern)
    'paleo': {
        name: 'Paleo',
        carbs: 25,      // Lower carbs from vegetables/fruits
        protein: 30,    // Higher protein from meat/fish
        fat: 45,        // Moderate-high fat from animal/plant sources
        description: 'No grains, legumes, dairy; emphasizes whole foods',
        source: 'European Journal of Clinical Nutrition'
    },

    // Pescatarian (similar to Mediterranean with fish focus)
    'pescatarian': {
        name: 'Pescatarian',
        carbs: 45,
        protein: 25,    // Fish as primary protein source
        fat: 30,        // Healthy omega-3 fats from fish
        description: 'Plant-based with fish/seafood; rich in omega-3s',
        source: 'American Heart Association'
    },

    // Gluten-Free (restriction, not macro-specific)
    'gluten-free': {
        name: 'Gluten-Free',
        carbs: 50,
        protein: 25,
        fat: 25,
        description: 'Standard macros, avoid gluten-containing grains',
        source: 'Celiac Disease Foundation'
    },

    // Dairy-Free (restriction, not macro-specific)
    'dairy-free': {
        name: 'Dairy-Free',
        carbs: 50,
        protein: 25,
        fat: 25,
        description: 'Standard macros, avoid dairy products',
        source: 'Academy of Nutrition and Dietetics'
    },

    // Low-Carb (moderate ketogenic)
    'low-carb': {
        name: 'Low-Carb',
        carbs: 20,      // 20-30% (100-150g typical)
        protein: 30,    // Higher protein for satiety
        fat: 50,        // Moderate-high fat
        description: 'Moderate carb restriction (100-150g/day typical)',
        source: 'Journal of Clinical Nutrition'
    }
};

/**
 * Protein multipliers based on goal (g per kg bodyweight)
 * Based on Examine.com protein guidelines (2023)
 */
export const PROTEIN_MULTIPLIERS = {
    'lose_weight': 1.8,     // Higher protein preserves muscle during deficit (1.6-2.4 range)
    'maintain': 1.4,        // Moderate protein for maintenance (1.2-1.6 range)
    'gain_muscle': 2.0,     // High protein for muscle synthesis (1.6-2.2 range)
};

/**
 * Calculate daily macro goals based on profile
 * 
 * @param {Object} profile - User profile with calorie_goal, weight, diet, goal
 * @returns {Object} - { protein: g, carbs: g, fat: g, distribution: {...}, source: string }
 */
export function calculateMacros(profile) {
    const {
        calorie_goal,
        weight,
        diet: rawDiet = '',
        goal = 'maintain'
    } = profile || {};

    // Normalize diet to lowercase for matching
    const diet = rawDiet?.toLowerCase()?.replace(/\s+/g, '-') || '';

    // Get diet-specific distribution
    const distribution = DIET_MACRO_DISTRIBUTIONS[diet] || DIET_MACRO_DISTRIBUTIONS[''];

    // Calculate calories from each macro
    // Protein: 4 cal/g, Carbs: 4 cal/g, Fat: 9 cal/g
    const calories = calorie_goal || 2000; // Default 2000 if not set

    // For protein, we also consider body weight and goal for more accuracy
    let proteinGrams;

    if (weight) {
        // Use weight-based calculation for protein
        const proteinMultiplier = PROTEIN_MULTIPLIERS[goal] || 1.4;
        proteinGrams = Math.round(weight * proteinMultiplier);

        // Calculate protein calories and percentage
        const proteinCalories = proteinGrams * 4;
        const proteinPercent = (proteinCalories / calories) * 100;

        // For special diets with 0 carbs (like carnivore, keto), respect the hard limit
        if (distribution.carbs === 0) {
            // Zero carb diet - all remaining calories go to fat
            const remainingCalories = calories - proteinCalories;
            const fatGrams = Math.round(remainingCalories / 9);

            return {
                protein: proteinGrams,
                carbs: 0,
                fat: fatGrams,
                calories,
                distribution: {
                    ...distribution,
                    actualProtein: Math.round(proteinPercent),
                    actualCarbs: 0,
                    actualFat: Math.round(100 - proteinPercent)
                },
                calculationMethod: 'weight-based protein (zero-carb diet)',
                source: distribution.source
            };
        }

        // For very low carb diets (keto), cap carbs at ~50g
        if (distribution.carbs <= 10) {
            const maxCarbGrams = 50; // Typical keto limit
            const carbCalories = maxCarbGrams * 4;
            const remainingCalories = calories - proteinCalories - carbCalories;
            const fatGrams = Math.round(remainingCalories / 9);

            return {
                protein: proteinGrams,
                carbs: maxCarbGrams,
                fat: fatGrams,
                calories,
                distribution: {
                    ...distribution,
                    actualProtein: Math.round(proteinPercent),
                    actualCarbs: Math.round((carbCalories / calories) * 100),
                    actualFat: Math.round((fatGrams * 9 / calories) * 100)
                },
                calculationMethod: 'weight-based protein (very low-carb diet)',
                source: distribution.source
            };
        }

        // Adjust carbs and fat based on remaining calories
        // Maintain the ratio between carbs and fat from the diet distribution
        const remainingCaloriesPercent = 100 - proteinPercent;
        const originalCarbsFatRatio = distribution.carbs / (distribution.carbs + distribution.fat);

        const adjustedCarbsPercent = remainingCaloriesPercent * originalCarbsFatRatio;
        const adjustedFatPercent = remainingCaloriesPercent * (1 - originalCarbsFatRatio);

        const carbsGrams = Math.round((calories * (adjustedCarbsPercent / 100)) / 4);
        const fatGrams = Math.round((calories * (adjustedFatPercent / 100)) / 9);

        return {
            protein: proteinGrams,
            carbs: carbsGrams,
            fat: fatGrams,
            calories,
            distribution: {
                ...distribution,
                // Updated percentages
                actualProtein: Math.round(proteinPercent),
                actualCarbs: Math.round(adjustedCarbsPercent),
                actualFat: Math.round(adjustedFatPercent)
            },
            calculationMethod: 'weight-based protein',
            source: distribution.source
        };
    }

    // Fallback: Use percentage-based calculation
    proteinGrams = Math.round((calories * (distribution.protein / 100)) / 4);
    const carbsGrams = Math.round((calories * (distribution.carbs / 100)) / 4);
    const fatGrams = Math.round((calories * (distribution.fat / 100)) / 9);

    return {
        protein: proteinGrams,
        carbs: carbsGrams,
        fat: fatGrams,
        calories,
        distribution: {
            ...distribution,
            actualProtein: distribution.protein,
            actualCarbs: distribution.carbs,
            actualFat: distribution.fat
        },
        calculationMethod: 'percentage-based',
        source: distribution.source
    };
}

/**
 * Get macro goals from profile, with intelligent fallback to calculated values
 * 
 * @param {Object} profile - User profile
 * @returns {Object} - { protein, carbs, fat, isCalculated, distribution }
 */
export function getMacroGoals(profile) {
    const calculated = calculateMacros(profile);

    // For special diets (keto, carnivore, low-carb), ALWAYS use calculated values
    // to ensure correct macro distribution regardless of stored values
    const rawDiet = profile?.diet || '';
    const normalizedDiet = rawDiet.toLowerCase().replace(/\s+/g, '-');
    const isSpecialDiet = ['keto', 'ketogenic', 'carnivore', 'low-carb', 'paleo'].includes(normalizedDiet);

    // Use calculated values for special diets, otherwise allow stored overrides
    let protein, carbs, fat;

    if (isSpecialDiet) {
        // Special diets: always use calculated values to ensure correct distribution
        protein = calculated.protein;
        carbs = calculated.carbs;
        fat = calculated.fat;
    } else {
        // Regular diets: use stored values if available
        protein = profile?.protein_goal || calculated.protein;
        carbs = profile?.carbs_goal || calculated.carbs;
        fat = profile?.fat_goal || calculated.fat;
    }

    // Check if using calculated vs stored values
    const isCalculated = isSpecialDiet || !profile?.protein_goal || !profile?.carbs_goal || !profile?.fat_goal;

    return {
        protein,
        carbs,
        fat,
        calories: profile?.calorie_goal || calculated.calories,
        isCalculated,
        distribution: calculated.distribution,
        source: calculated.source
    };
}

/**
 * Format macro display with percentage
 * 
 * @param {number} grams - Grams of macro
 * @param {number} calories - Total daily calories
 * @param {number} calPerGram - Calories per gram (4 for protein/carbs, 9 for fat)
 * @returns {string} - Formatted string like "150g (30%)"
 */
export function formatMacroWithPercent(grams, calories, calPerGram = 4) {
    const macroCalories = grams * calPerGram;
    const percent = Math.round((macroCalories / calories) * 100);
    return `${grams}g (${percent}%)`;
}

/**
 * Get diet info with macro distribution
 * 
 * @param {string} dietId - Diet type ID
 * @returns {Object} - Diet information including macro distribution
 */
export function getDietInfo(dietId) {
    // Normalize diet ID to lowercase with hyphens
    const normalizedDiet = dietId?.toLowerCase()?.replace(/\s+/g, '-') || '';
    return DIET_MACRO_DISTRIBUTIONS[normalizedDiet] || DIET_MACRO_DISTRIBUTIONS[''];
}

/**
 * Calculate if macros are balanced for a given diet
 * 
 * @param {Object} currentMacros - { protein, carbs, fat } in grams
 * @param {Object} goals - { protein, carbs, fat } in grams
 * @returns {Object} - { isBalanced, deficits, surpluses }
 */
export function analyzeMacroBalance(currentMacros, goals) {
    const analyze = (current, goal, name) => {
        const percent = (current / goal) * 100;
        return {
            name,
            current,
            goal,
            percent: Math.round(percent),
            deficit: Math.max(0, goal - current),
            surplus: Math.max(0, current - goal),
            status: percent >= 90 && percent <= 110 ? 'on-track' :
                percent < 90 ? 'deficit' : 'surplus'
        };
    };

    const analysis = {
        protein: analyze(currentMacros.protein || 0, goals.protein, 'Protein'),
        carbs: analyze(currentMacros.carbs || 0, goals.carbs, 'Carbs'),
        fat: analyze(currentMacros.fat || 0, goals.fat, 'Fat')
    };

    const allOnTrack = Object.values(analysis).every(a => a.status === 'on-track');
    const deficits = Object.values(analysis).filter(a => a.status === 'deficit');
    const surpluses = Object.values(analysis).filter(a => a.status === 'surplus');

    return {
        isBalanced: allOnTrack,
        deficits,
        surpluses,
        analysis
    };
}
