/**
 * SafetyMessage - Graceful decline for medical/medication questions
 *
 * Displays empathetic responses when users ask about:
 * - Medications, dosages, drug interactions
 * - Medical diagnoses or symptoms
 * - Treatment recommendations
 *
 * Features:
 * - Warm, empathetic tone (not robotic)
 * - Clear explanation of limitations
 * - Helpful alternatives (consult doctor)
 * - What we CAN help with
 * - Professional styling (amber/warm, not scary red)
 */

import { useState } from 'react'
import {
    Heart,
    Shield,
    Stethoscope,
    ChevronDown,
    ChevronUp,
    Sparkles,
    MessageCircle,
    Apple,
    Scale,
    Utensils,
    Activity,
    ExternalLink,
    Phone,
    AlertTriangle
} from 'lucide-react'

/**
 * Safety response types with customized messaging
 */
const SAFETY_TYPES = {
    medication: {
        icon: Shield,
        title: "I can't provide medication advice",
        color: '#F59E0B',
        bgGradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.05) 100%)',
        borderColor: 'rgba(245, 158, 11, 0.3)',
        reason: "Medication dosages and interactions require professional medical evaluation based on your complete health history, current medications, and individual factors that I don't have access to.",
        alternatives: [
            { icon: Stethoscope, text: 'Consult your doctor or pharmacist' },
            { icon: Phone, text: 'Call a health helpline for guidance' },
            { icon: ExternalLink, text: 'Visit a licensed telehealth service' }
        ]
    },
    diagnosis: {
        icon: Stethoscope,
        title: "I can't diagnose health conditions",
        color: '#F59E0B',
        bgGradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.05) 100%)',
        borderColor: 'rgba(245, 158, 11, 0.3)',
        reason: "Diagnosing symptoms requires a physical examination, medical tests, and professional training. What seems like one condition could have many different causes.",
        alternatives: [
            { icon: Stethoscope, text: 'Schedule an appointment with your doctor' },
            { icon: Phone, text: 'For urgent symptoms, seek immediate care' },
            { icon: ExternalLink, text: 'Use symptom checkers as a starting point only' }
        ]
    },
    treatment: {
        icon: Heart,
        title: "I can't recommend medical treatments",
        color: '#F59E0B',
        bgGradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.05) 100%)',
        borderColor: 'rgba(245, 158, 11, 0.3)',
        reason: "Treatment decisions depend on your specific diagnosis, health history, and circumstances. What works for one person may not be safe or effective for another.",
        alternatives: [
            { icon: Stethoscope, text: 'Discuss treatment options with your healthcare provider' },
            { icon: MessageCircle, text: 'Seek a second opinion if needed' },
            { icon: ExternalLink, text: 'Research from reputable medical sources' }
        ]
    },
    emergency: {
        icon: AlertTriangle,
        title: "This sounds like it needs immediate attention",
        color: '#EF4444',
        bgGradient: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(220, 38, 38, 0.05) 100%)',
        borderColor: 'rgba(239, 68, 68, 0.3)',
        reason: "If you or someone else is experiencing a medical emergency, please don't wait for online advice.",
        alternatives: [
            { icon: Phone, text: 'Call emergency services (911) immediately' },
            { icon: Stethoscope, text: 'Go to your nearest emergency room' },
            { icon: MessageCircle, text: 'Call a poison control center if relevant' }
        ],
        isUrgent: true
    },
    supplement: {
        icon: Shield,
        title: "A note about supplement advice",
        color: '#8B5CF6',
        bgGradient: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(124, 58, 237, 0.05) 100%)',
        borderColor: 'rgba(139, 92, 246, 0.3)',
        reason: "The information below is based on nutritional research. For personalised advice — especially if you take medication — please consult your doctor or pharmacist.",
        compact: true, // render as a small inline banner, not the full card
        alternatives: [
            { icon: Stethoscope, text: 'Consult your doctor before starting supplements' },
            { icon: Phone, text: 'Ask your pharmacist about interactions' },
            { icon: ExternalLink, text: 'Get blood work to check nutrient levels' }
        ]
    }
}

/**
 * Things we CAN help with
 */
const CAN_HELP_WITH = [
    { icon: Apple, text: 'Nutrition information & healthy eating tips', color: '#10B981' },
    { icon: Utensils, text: 'Meal planning & recipe suggestions', color: '#3B82F6' },
    { icon: Scale, text: 'General wellness & weight management guidance', color: '#8B5CF6' },
    { icon: Activity, text: 'Understanding food labels & nutrients', color: '#EC4899' }
]

/**
 * Alternative suggestion tip (non-clickable, informational only)
 */
const AlternativeTip = ({ icon: Icon, text, color }) => (
    <div
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
        style={{
            background: `${color}12`,
            border: `1px solid ${color}30`,
            color: 'var(--color-text-secondary)'
        }}
    >
        <Icon className="w-4 h-4 shrink-0" style={{ color }} />
        <span>{text}</span>
    </div>
)

/**
 * "What I CAN help with" card
 */
const CanHelpCard = ({ icon: Icon, text, color }) => (
    <div
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
        style={{
            background: `${color}10`,
            border: `1px solid ${color}25`
        }}
    >
        <div
            className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
            style={{ background: `${color}20` }}
        >
            <Icon className="w-3.5 h-3.5" style={{ color }} />
        </div>
        <span style={{ color: 'var(--color-text-secondary)' }}>{text}</span>
    </div>
)

/**
 * Main SafetyMessage component
 */
export const SafetyMessage = ({
    type = 'medication', // 'medication' | 'diagnosis' | 'treatment' | 'emergency'
    customMessage,
    showAlternatives = true,
    showCanHelp = true,
    className = ''
}) => {
    const [isExpanded, setIsExpanded] = useState(false)
    const config = SAFETY_TYPES[type] || SAFETY_TYPES.medication
    const Icon = config.icon

    // Compact inline banner for supplement-type notices
    if (config.compact) {
        return (
            <div
                className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg animate-fadeIn ${className}`}
                style={{
                    background: config.bgGradient,
                    border: `1px solid ${config.borderColor}`
                }}
            >
                <Icon className="w-4 h-4 shrink-0" style={{ color: config.color }} />
                <p className="text-sm leading-snug" style={{ color: 'var(--color-text-secondary)' }}>
                    {customMessage || config.reason}
                </p>
            </div>
        )
    }

    return (
        <div
            className={`rounded-xl overflow-hidden animate-fadeIn ${className}`}
            style={{
                background: config.bgGradient,
                border: `1px solid ${config.borderColor}`
            }}
        >
            {/* Header */}
            <div className="p-4">
                <div className="flex items-start gap-3">
                    {/* Icon with glow */}
                    <div className="relative shrink-0">
                        <div
                            className="absolute inset-0 rounded-xl blur-md opacity-40"
                            style={{ background: config.color }}
                        />
                        <div
                            className="relative w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{
                                background: `linear-gradient(135deg, ${config.color} 0%, ${config.color}dd 100%)`,
                                boxShadow: `0 4px 12px ${config.color}40`
                            }}
                        >
                            <Icon className="w-5 h-5 text-white" />
                        </div>
                    </div>

                    {/* Title and message */}
                    <div className="flex-1 min-w-0">
                        <h3
                            className="text-base font-semibold mb-1"
                            style={{ color: config.color }}
                        >
                            {config.title}
                        </h3>
                        <p
                            className="text-sm leading-relaxed"
                            style={{ color: 'var(--color-text-secondary)' }}
                        >
                            {customMessage || config.reason}
                        </p>
                    </div>
                </div>

                {/* Tips */}
                {showAlternatives && (
                    <div className="mt-4 flex flex-col gap-2">
                        {config.alternatives.map((alt, i) => (
                            <AlternativeTip
                                key={i}
                                icon={alt.icon}
                                text={alt.text}
                                color={config.color}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Expandable "What I CAN help with" section */}
            {showCanHelp && !config.isUrgent && (
                <>
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="w-full px-4 py-3 flex items-center justify-center gap-2 border-t transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                        style={{ borderColor: config.borderColor }}
                    >
                        <Sparkles className="w-4 h-4" style={{ color: '#10B981' }} />
                        <span className="text-sm font-medium" style={{ color: '#10B981' }}>
                            But here's what I can help with
                        </span>
                        {isExpanded ? (
                            <ChevronUp className="w-4 h-4" style={{ color: '#10B981' }} />
                        ) : (
                            <ChevronDown className="w-4 h-4" style={{ color: '#10B981' }} />
                        )}
                    </button>

                    {isExpanded && (
                        <div
                            className="px-4 pb-4 border-t animate-fadeIn"
                            style={{ borderColor: config.borderColor }}
                        >
                            <div className="pt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {CAN_HELP_WITH.map((item, i) => (
                                    <CanHelpCard key={i} {...item} />
                                ))}
                            </div>

                            {/* Friendly prompt */}
                            <div
                                className="mt-3 p-3 rounded-lg text-sm text-center"
                                style={{
                                    background: 'rgba(16, 185, 129, 0.08)',
                                    border: '1px solid rgba(16, 185, 129, 0.2)',
                                    color: '#10B981'
                                }}
                            >
                                <Heart className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
                                Feel free to ask me about any of these topics!
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

/**
 * Compact inline safety notice
 */
export const SafetyNotice = ({
    message = "This is general information only, not medical advice.",
    className = ''
}) => (
    <div
        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${className}`}
        style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            color: '#D97706'
        }}
    >
        <Shield className="w-3.5 h-3.5 shrink-0" />
        <span>{message}</span>
    </div>
)

/**
 * Pre-built safety response templates
 */
export const SafetyResponses = {
    medication: (medicationName) => ({
        type: 'medication',
        customMessage: medicationName
            ? `I understand you're asking about ${medicationName}. While I'd love to help, medication advice requires professional medical evaluation. Your doctor or pharmacist can give you accurate, personalized guidance.`
            : "I understand you're looking for medication guidance. While I'd love to help, this requires professional medical evaluation based on your complete health picture."
    }),

    diagnosis: (symptom) => ({
        type: 'diagnosis',
        customMessage: symptom
            ? `I can see you're concerned about ${symptom}. I wish I could give you answers, but diagnosing symptoms really needs a proper medical evaluation. Your doctor can examine you and run any necessary tests.`
            : "I understand you're worried about these symptoms. While I wish I could help diagnose what's going on, that really requires a professional evaluation."
    }),

    treatment: (condition) => ({
        type: 'treatment',
        customMessage: condition
            ? `I know you're looking for treatment options for ${condition}. This is something your healthcare provider can best advise on, as they can consider your full medical history and specific situation.`
            : "I understand you want treatment recommendations. This is something your healthcare provider can best advise on, considering your specific situation."
    }),

    drugInteraction: (drugs) => ({
        type: 'medication',
        customMessage: `Checking drug interactions is really important, and I'm glad you're thinking about safety. However, I can't reliably assess interactions between ${drugs || 'medications'}. Your pharmacist is the expert here and can check this for you quickly.`
    }),

    dosage: (medication) => ({
        type: 'medication',
        customMessage: `Dosage for ${medication || 'medications'} depends on many individual factors like your age, weight, kidney function, and other medications. Your prescribing doctor or pharmacist can tell you the right dose for you.`
    })
}

/**
 * Utility to detect if a message needs a safety response
 */
export const detectSafetyTrigger = (message) => {
    const lowerMessage = message.toLowerCase()

    // Emergency patterns
    const emergencyPatterns = [
        /chest pain/i, /can't breathe/i, /overdose/i, /suicide/i,
        /heart attack/i, /stroke/i, /severe bleeding/i, /unconscious/i
    ]
    if (emergencyPatterns.some(p => p.test(message))) {
        return { type: 'emergency', detected: true }
    }

    // Medication patterns
    const medicationPatterns = [
        /how much .* should i take/i, /dosage/i, /mg.*per day/i,
        /can i take .* with/i, /drug interaction/i, /side effect/i,
        /is it safe to take/i, /overdose/i, /prescription/i
    ]
    if (medicationPatterns.some(p => p.test(message))) {
        return { type: 'medication', detected: true }
    }

    // Diagnosis patterns
    const diagnosisPatterns = [
        /do i have/i, /is this .* cancer/i, /diagnose/i,
        /what disease/i, /what condition/i, /symptoms of/i
    ]
    if (diagnosisPatterns.some(p => p.test(message))) {
        return { type: 'diagnosis', detected: true }
    }

    // Treatment patterns
    const treatmentPatterns = [
        /how to treat/i, /cure for/i, /best treatment/i,
        /should i get surgery/i, /therapy for/i
    ]
    if (treatmentPatterns.some(p => p.test(message))) {
        return { type: 'treatment', detected: true }
    }

    return { type: null, detected: false }
}

export default SafetyMessage
