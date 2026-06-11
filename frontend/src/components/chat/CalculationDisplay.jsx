/**
 * CalculationDisplay - Shows nutritional calculations with formulas
 *
 * Displays BMR, TDEE, and macro calculations with:
 * - Linear step-by-step flow
 * - Formula with substituted values
 * - Expandable "How was this calculated?" section
 * - Professional styling with icons
 */

import { useState } from 'react'
import {
    Calculator,
    ChevronDown,
    ChevronUp,
    Flame,
    Activity,
    Target,
    Zap,
    HelpCircle,
    CheckCircle2
} from 'lucide-react'

/**
 * Activity level multipliers (handles multiple naming conventions)
 */
const ACTIVITY_MULTIPLIERS = {
    sedentary: { label: 'Sedentary', multiplier: 1.2, desc: 'Little or no exercise' },
    light: { label: 'Lightly Active', multiplier: 1.375, desc: 'Light exercise 1-3 days/week' },
    lightly_active: { label: 'Lightly Active', multiplier: 1.375, desc: 'Light exercise 1-3 days/week' },
    moderate: { label: 'Moderately Active', multiplier: 1.55, desc: 'Moderate exercise 3-5 days/week' },
    moderately_active: { label: 'Moderately Active', multiplier: 1.55, desc: 'Moderate exercise 3-5 days/week' },
    active: { label: 'Very Active', multiplier: 1.725, desc: 'Hard exercise 6-7 days/week' },
    very_active: { label: 'Very Active', multiplier: 1.725, desc: 'Hard exercise 6-7 days/week' },
    extreme: { label: 'Extremely Active', multiplier: 1.9, desc: 'Very hard exercise, physical job' },
    extremely_active: { label: 'Extremely Active', multiplier: 1.9, desc: 'Very hard exercise, physical job' }
}

/**
 * Goal adjustments (handles multiple naming conventions)
 */
const GOAL_INFO = {
    lose: { label: 'Weight Loss', adjustment: -500, color: '#EF4444' },
    lose_weight: { label: 'Weight Loss', adjustment: -500, color: '#EF4444' },
    maintain: { label: 'Maintain', adjustment: 0, color: '#10B981' },
    gain: { label: 'Muscle Gain', adjustment: 300, color: '#3B82F6' },
    gain_muscle: { label: 'Muscle Gain', adjustment: 300, color: '#3B82F6' }
}

/**
 * Format number with commas
 */
const formatNumber = (num) => {
    return Math.round(num).toLocaleString()
}

/**
 * Single calculation step component
 */
const CalculationStep = ({ stepNumber, icon: Icon, iconColor, title, subtitle, formula, result, unit = 'kcal' }) => (
    <div className="flex gap-3">
        {/* Step indicator line */}
        <div className="flex flex-col items-center">
            <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                style={{
                    background: `linear-gradient(135deg, ${iconColor} 0%, ${iconColor}dd 100%)`,
                    boxShadow: `0 2px 8px ${iconColor}40`
                }}
            >
                {stepNumber}
            </div>
            <div
                className="w-0.5 flex-1 my-1"
                style={{ background: 'var(--color-border)' }}
            />
        </div>

        {/* Step content */}
        <div className="flex-1 pb-4">
            {/* Title row */}
            <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4" style={{ color: iconColor }} />
                <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {title}
                </span>
            </div>

            {/* Subtitle/formula name */}
            {subtitle && (
                <div className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
                    {subtitle}
                </div>
            )}

            {/* Formula with values */}
            <div
                className="font-mono text-sm p-2.5 rounded-lg mb-2"
                style={{
                    background: 'var(--color-bg-secondary)',
                    color: 'var(--color-text-secondary)'
                }}
            >
                {formula}
            </div>

            {/* Result */}
            <div
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold"
                style={{
                    background: `${iconColor}15`,
                    color: iconColor
                }}
            >
                <CheckCircle2 className="w-4 h-4" />
                {formatNumber(result)} {unit}
            </div>
        </div>
    </div>
)

/**
 * Final result component
 */
const FinalResult = ({ calories, label = "Daily Calorie Target" }) => (
    <div
        className="flex items-center justify-between p-4 rounded-xl"
        style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.3)'
        }}
    >
        <div className="flex items-center gap-3">
            <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{
                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                }}
            >
                <Target className="w-5 h-5 text-white" />
            </div>
            <div>
                <div className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                    {label}
                </div>
                <div className="text-xl font-bold" style={{ color: '#10B981' }}>
                    {formatNumber(calories)} kcal/day
                </div>
            </div>
        </div>
    </div>
)

/**
 * Main CalculationDisplay component
 */
export const CalculationDisplay = ({ calculations, className = '' }) => {
    const [isExpanded, setIsExpanded] = useState(false)

    if (!calculations) return null

    const { weight, height, age, gender, bmr, tdee, activityLevel, goal, targetCalories } = calculations

    // Check if we have enough data
    const hasBMR = bmr && weight && height && age
    if (!hasBMR) return null

    const isMale = gender?.toLowerCase().startsWith('m')
    const genderAdjustment = isMale ? 5 : -161
    const genderSign = isMale ? '+' : ''

    const activity = ACTIVITY_MULTIPLIERS[activityLevel] || ACTIVITY_MULTIPLIERS.moderate
    const currentGoal = GOAL_INFO[goal] || GOAL_INFO.maintain

    // Use targetCalories from backend if available, otherwise calculate
    const finalCalories = targetCalories || ((tdee || bmr) + currentGoal.adjustment)

    return (
        <div
            className={`mt-4 rounded-xl overflow-hidden ${className}`}
            style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)'
            }}
        >
            {/* Header - Always visible */}
            <div className="p-4">
                <FinalResult calories={finalCalories} />
            </div>

            {/* Expandable section */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-3 flex items-center justify-center gap-2 border-t transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                style={{ borderColor: 'var(--color-border)' }}
            >
                <HelpCircle className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                    How was this calculated?
                </span>
                {isExpanded ? (
                    <ChevronUp className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                ) : (
                    <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                )}
            </button>

            {/* Expanded calculation steps */}
            {isExpanded && (
                <div
                    className="px-4 pb-4 border-t animate-fadeIn"
                    style={{ borderColor: 'var(--color-border)' }}
                >
                    <div className="pt-4">
                        {/* Step 1: BMR */}
                        <CalculationStep
                            stepNumber={1}
                            icon={Flame}
                            iconColor="#F59E0B"
                            title="Basal Metabolic Rate (BMR)"
                            subtitle="Mifflin-St Jeor Equation"
                            formula={`(10 × ${weight}kg) + (6.25 × ${height}cm) - (5 × ${age}) ${genderSign}${genderAdjustment} = ${formatNumber(bmr)}`}
                            result={bmr}
                        />

                        {/* Step 2: Activity Multiplier */}
                        <CalculationStep
                            stepNumber={2}
                            icon={Zap}
                            iconColor="#3B82F6"
                            title="Activity Multiplier"
                            subtitle={`${activity.label} - ${activity.desc}`}
                            formula={`Multiplier = ${activity.multiplier}`}
                            result={activity.multiplier}
                            unit=""
                        />

                        {/* Step 3: TDEE */}
                        {tdee && (
                            <CalculationStep
                                stepNumber={3}
                                icon={Activity}
                                iconColor="#8B5CF6"
                                title="Total Daily Energy Expenditure (TDEE)"
                                subtitle="BMR × Activity Multiplier"
                                formula={`${formatNumber(bmr)} × ${activity.multiplier} = ${formatNumber(tdee)}`}
                                result={tdee}
                            />
                        )}

                        {/* Step 4: Goal Adjustment */}
                        <div className="flex gap-3">
                            <div className="flex flex-col items-center">
                                <div
                                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                                    style={{
                                        background: `linear-gradient(135deg, #10B981 0%, #059669 100%)`,
                                        boxShadow: '0 2px 8px rgba(16, 185, 129, 0.4)'
                                    }}
                                >
                                    {tdee ? 4 : 3}
                                </div>
                            </div>

                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <Target className="w-4 h-4" style={{ color: '#10B981' }} />
                                    <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                        Goal Adjustment
                                    </span>
                                </div>

                                <div className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
                                    {currentGoal.label} = {currentGoal.adjustment >= 0 ? '+' : ''}{currentGoal.adjustment} kcal
                                </div>

                                <div
                                    className="font-mono text-sm p-2.5 rounded-lg mb-2"
                                    style={{
                                        background: 'var(--color-bg-secondary)',
                                        color: 'var(--color-text-secondary)'
                                    }}
                                >
                                    {formatNumber(tdee || bmr)} {currentGoal.adjustment >= 0 ? '+' : ''} {currentGoal.adjustment} = {formatNumber(finalCalories)}
                                </div>

                                <div
                                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold"
                                    style={{
                                        background: 'rgba(16, 185, 129, 0.15)',
                                        color: '#10B981'
                                    }}
                                >
                                    <CheckCircle2 className="w-4 h-4" />
                                    Final: {formatNumber(finalCalories)} kcal/day
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default CalculationDisplay
