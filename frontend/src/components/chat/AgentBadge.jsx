/**
 * AgentBadge - Visual indicator for which agent answered
 * 
 * Shows the specialized agent that processed the query:
 * - Science Agent (research queries)
 * - Nutrition Agent (dietary advice)
 * - Profile Agent (user data)
 * - Meal Planner (meal logging)
 * - Chat Agent (general conversation)
 */

import { useState } from 'react'
import {
    FlaskConical,
    Apple,
    User,
    UtensilsCrossed,
    MessageCircle,
    Sparkles,
    Bot,
    ChevronDown,
    ChevronUp,
    Wrench,
    CheckCircle
} from 'lucide-react'

// Agent configurations
const agents = {
    science: {
        name: 'Science Agent',
        icon: FlaskConical,
        gradient: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
        bgColor: 'rgba(139, 92, 246, 0.1)',
        borderColor: 'rgba(139, 92, 246, 0.3)',
        textColor: '#8B5CF6',
        description: 'Research-backed answer'
    },
    nutrition: {
        name: 'Nutrition Agent',
        icon: Apple,
        gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        bgColor: 'rgba(16, 185, 129, 0.1)',
        borderColor: 'rgba(16, 185, 129, 0.3)',
        textColor: '#10B981',
        description: 'Dietary expertise'
    },
    profile: {
        name: 'Profile Agent',
        icon: User,
        gradient: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
        bgColor: 'rgba(59, 130, 246, 0.1)',
        borderColor: 'rgba(59, 130, 246, 0.3)',
        textColor: '#3B82F6',
        description: 'Profile management'
    },
    meal: {
        name: 'Meal Planner',
        icon: UtensilsCrossed,
        gradient: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        borderColor: 'rgba(245, 158, 11, 0.3)',
        textColor: '#F59E0B',
        description: 'Meal tracking'
    },
    chat: {
        name: 'Chat Agent',
        icon: MessageCircle,
        gradient: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
        bgColor: 'rgba(107, 114, 128, 0.1)',
        borderColor: 'rgba(107, 114, 128, 0.3)',
        textColor: '#6B7280',
        description: 'General assistance'
    }
}

/**
 * Compact badge for inline display
 */
export const AgentBadgeCompact = ({ intent, sources, className = '' }) => {
    // Determine agent based on intent or sources
    let agentKey = 'chat'
    if (intent === 'science' || sources?.length > 0) {
        agentKey = 'science'
    } else if (intent === 'nutrition') {
        agentKey = 'nutrition'
    } else if (intent === 'profile') {
        agentKey = 'profile'
    } else if (intent === 'meal' || intent === 'meal_log' || intent === 'meal_planner') {
        agentKey = 'meal'
    }

    const agent = agents[agentKey]
    const Icon = agent.icon

    return (
        <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${className}`}
            style={{
                background: agent.bgColor,
                border: `1px solid ${agent.borderColor}`,
                color: agent.textColor
            }}
        >
            <span
                className="w-1.5 h-1.5 rounded-full animate-pulse"
                style={{ background: agent.textColor }}
            />
            <Icon className="w-3 h-3" />
            <span>{agent.name}</span>
        </div>
    )
}

/**
 * Detailed badge with icon and description
 */
export const AgentBadgeDetailed = ({ intent, sources, toolsUsed, className = '' }) => {
    // Determine agent based on intent, sources, or tools used
    let agentKey = 'chat'
    if (intent === 'science' || sources?.length > 0) {
        agentKey = 'science'
    } else if (intent === 'nutrition') {
        agentKey = 'nutrition'
    } else if (intent === 'profile') {
        agentKey = 'profile'
    } else if (intent === 'meal' || intent === 'meal_log' || intent === 'meal_planner') {
        agentKey = 'meal'
    }

    const agent = agents[agentKey]
    const Icon = agent.icon

    return (
        <div
            className={`flex items-center gap-3 p-3 rounded-xl ${className}`}
            style={{
                background: agent.bgColor,
                border: `1px solid ${agent.borderColor}`
            }}
        >
            {/* Icon */}
            <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                style={{
                    background: agent.gradient,
                    boxShadow: `0 4px 12px ${agent.textColor}40`
                }}
            >
                <Icon className="w-4 h-4 text-white" />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span
                        className="text-sm font-semibold"
                        style={{ color: agent.textColor }}
                    >
                        {agent.name}
                    </span>
                    <Sparkles className="w-3 h-3" style={{ color: agent.textColor }} />
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {agent.description}
                </div>
            </div>

            {/* Tools used indicator */}
            {toolsUsed && toolsUsed.length > 0 && (
                <div
                    className="px-2 py-1 rounded-lg text-xs"
                    style={{
                        background: 'var(--color-bg-secondary)',
                        color: 'var(--color-text-muted)'
                    }}
                >
                    {toolsUsed.length} tool{toolsUsed.length > 1 ? 's' : ''} used
                </div>
            )}
        </div>
    )
}

/**
 * Mini badge for message header
 */
export const AgentBadgeMini = ({ intent, sources, className = '' }) => {
    // Determine agent
    let agentKey = 'chat'
    if (intent === 'science' || sources?.length > 0) {
        agentKey = 'science'
    } else if (intent === 'nutrition') {
        agentKey = 'nutrition'
    } else if (intent === 'profile') {
        agentKey = 'profile'
    } else if (intent === 'meal' || intent === 'meal_log' || intent === 'meal_planner') {
        agentKey = 'meal'
    }

    const agent = agents[agentKey]
    const Icon = agent.icon

    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${className}`}
            style={{
                background: agentKey === 'science' ? agent.gradient : agent.bgColor,
                color: agentKey === 'science' ? 'white' : agent.textColor,
                border: agentKey === 'science' ? 'none' : `1px solid ${agent.borderColor}`
            }}
        >
            <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: agentKey === 'science' ? 'white' : agent.textColor }}
            />
            {agent.name}
        </span>
    )
}

/**
 * AgentBadgeProgressive - Progressive Disclosure variant
 * Shows simple badge that expands to reveal agent details
 * 
 * Used to make the Agentic AI architecture visible without overwhelming users
 */
export function AgentBadgeProgressive({
    intent,
    sources = [],
    agentInfo = null,
    confidence = null,
    toolsUsed = [],
    className = ''
}) {
    const [isExpanded, setIsExpanded] = useState(false)

    // Determine which agent based on intent or agentInfo from backend
    let agentKey = agentInfo?.type || 'chat'

    // Fallback to intent-based detection
    if (!agentInfo?.type) {
        if (intent === 'science' || sources?.length > 0) {
            agentKey = 'science'
        } else if (intent === 'nutrition') {
            agentKey = 'nutrition'
        } else if (intent === 'profile') {
            agentKey = 'profile'
        } else if (intent === 'meal' || intent === 'meal_log') {
            agentKey = 'meal'
        }
    }

    const agent = agents[agentKey]
    const Icon = agent.icon

    // Format confidence as percentage
    const confidencePercent = confidence !== null ? Math.round(confidence * 100) : null

    // Format tools for display
    const formatTool = (tool) => {
        const toolNames = {
            'search_papers': 'Scientific Search',
            'search_nutrition': 'Nutrition Database',
            'calculate_nutrition': 'Nutrition Calculator',
            'meal_planning': 'Meal Planner',
            'get_profile': 'User Profile',
            'update_profile': 'Profile Update',
            'rerank_documents': 'Document Reranking',
            'web_search': 'Web Search'
        }
        return toolNames[tool] || tool
    }

    return (
        <div className={`inline-block ${className}`}>
            {/* Simple Badge - Shows agent name only */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:shadow-md cursor-pointer group`}
                style={{
                    background: agent.bgColor,
                    color: agent.textColor,
                    border: `1px solid ${agent.borderColor}`
                }}
                title="Click to see how this answer was generated"
            >
                <span className="font-semibold">{agentInfo?.name || agent.name}</span>
                <span className="opacity-40 group-hover:opacity-100 transition-opacity ml-0.5">
                    {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </span>
            </button>

            {/* Expanded Details - Only visible when clicked */}
            {isExpanded && (
                <div
                    className="mt-2 p-3 rounded-lg border text-xs space-y-2 animate-fadeIn"
                    style={{
                        background: 'rgba(255,255,255,0.95)',
                        borderColor: agent.borderColor
                    }}
                >
                    {/* Agent Description */}
                    <div className="flex items-start gap-2">
                        <Bot className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                        <div>
                            <p className="font-medium text-gray-700">AI Agent</p>
                            <p className="text-gray-500">{agentInfo?.description || agent.description}</p>
                        </div>
                    </div>

                    {/* Tools used */}
                    {toolsUsed && toolsUsed.length > 0 && (
                        <div className="flex items-start gap-2">
                            <Wrench className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                            <div>
                                <p className="font-medium text-gray-700">Tools Used</p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {toolsUsed.map((tool, idx) => (
                                        <span
                                            key={idx}
                                            className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-[10px]"
                                        >
                                            {formatTool(tool)}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Sources indicator */}
                    {sources && sources.length > 0 && (
                        <div className="flex items-start gap-2">
                            <Sparkles className="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
                            <div>
                                <p className="font-medium text-gray-700">Scientific Sources</p>
                                <p className="text-gray-500">{sources.length} peer-reviewed paper{sources.length > 1 ? 's' : ''} referenced</p>
                            </div>
                        </div>
                    )}

                    {/* Transparency note */}
                    <div className="pt-2 border-t border-gray-100 text-[10px] text-gray-400 italic">
                        This response was generated by a specialized AI agent
                    </div>
                </div>
            )}
        </div>
    )
}

export default AgentBadgeCompact
