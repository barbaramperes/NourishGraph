/**
 * LoadingStates - Professional loading components
 *
 * Includes:
 * - Skeleton loaders for various content types
 * - Typing indicator for chat
 * - Button loading states
 * - Spinner variants
 * - Pulse animations
 */

import { Loader2, MessageSquare } from 'lucide-react'

/**
 * Basic skeleton pulse animation
 */
const pulseStyle = {
    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    background: 'linear-gradient(90deg, var(--color-bg-secondary) 25%, var(--color-bg-tertiary) 50%, var(--color-bg-secondary) 75%)',
    backgroundSize: '200% 100%',
}

/**
 * Skeleton base component
 */
export const Skeleton = ({ className = '', width, height, rounded = 'lg', style = {} }) => (
    <div
        className={`animate-pulse rounded-${rounded} ${className}`}
        style={{
            width: width || '100%',
            height: height || '1rem',
            background: 'var(--color-bg-secondary)',
            ...style
        }}
    />
)

/**
 * Text skeleton - mimics text lines
 */
export const SkeletonText = ({ lines = 3, className = '' }) => (
    <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
            <Skeleton
                key={i}
                height="0.875rem"
                width={i === lines - 1 ? '60%' : '100%'}
                rounded="md"
            />
        ))}
    </div>
)

/**
 * Card skeleton - for loading cards
 */
export const SkeletonCard = ({ className = '' }) => (
    <div
        className={`p-4 rounded-xl ${className}`}
        style={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)'
        }}
    >
        <div className="flex items-center gap-3 mb-4">
            <Skeleton width="3rem" height="3rem" rounded="xl" />
            <div className="flex-1 space-y-2">
                <Skeleton height="1rem" width="60%" rounded="md" />
                <Skeleton height="0.75rem" width="40%" rounded="md" />
            </div>
        </div>
        <SkeletonText lines={2} />
    </div>
)

/**
 * Chat message skeleton
 */
export const SkeletonChatMessage = ({ isUser = false, className = '' }) => (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} ${className}`}>
        <Skeleton width="2.5rem" height="2.5rem" rounded="xl" />
        <div
            className={`flex-1 max-w-[80%] p-4 rounded-2xl ${isUser ? 'ml-auto' : ''}`}
            style={{
                background: isUser ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                opacity: 0.6
            }}
        >
            <SkeletonText lines={isUser ? 1 : 3} />
        </div>
    </div>
)

/**
 * Profile skeleton
 */
export const SkeletonProfile = ({ className = '' }) => (
    <div
        className={`rounded-xl overflow-hidden ${className}`}
        style={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)'
        }}
    >
        {/* Header */}
        <div className="p-4" style={{ background: 'rgba(16, 185, 129, 0.05)' }}>
            <div className="flex items-center gap-3">
                <Skeleton width="3.5rem" height="3.5rem" rounded="xl" />
                <div className="flex-1 space-y-2">
                    <Skeleton height="1.25rem" width="50%" rounded="md" />
                    <Skeleton height="0.75rem" width="30%" rounded="md" />
                </div>
            </div>
        </div>
        {/* Content */}
        <div className="p-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} height="4rem" rounded="xl" />
                ))}
            </div>
        </div>
    </div>
)

/**
 * Dashboard skeleton
 */
export const SkeletonDashboard = ({ className = '' }) => (
    <div className={`space-y-6 ${className}`}>
        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonCard key={i} />
            ))}
        </div>
        {/* Main content */}
        <div className="grid sm:grid-cols-2 gap-4">
            <SkeletonCard />
            <SkeletonCard />
        </div>
    </div>
)

/**
 * Chat typing indicator - animated dots
 */
export const TypingIndicator = ({ agentName = 'NutriBot', className = '' }) => (
    <div className={`flex gap-3 ${className}`}>
        {/* Avatar */}
        <div
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{
                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
            }}
        >
            <MessageSquare className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </div>

        {/* Typing bubble */}
        <div
            className="px-4 py-3 rounded-2xl rounded-tl-md"
            style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)'
            }}
        >
            <div className="flex items-center gap-1">
                <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                        <div
                            key={i}
                            className="w-2 h-2 rounded-full"
                            style={{
                                background: '#10B981',
                                animation: `bounce 1.4s infinite ease-in-out both`,
                                animationDelay: `${i * 0.16}s`
                            }}
                        />
                    ))}
                </div>
            </div>
        </div>
    </div>
)

/**
 * Button with loading state
 */
export const LoadingButton = ({
    children,
    loading = false,
    loadingText = 'Loading...',
    disabled = false,
    onClick,
    variant = 'primary', // primary | secondary | danger
    size = 'md', // sm | md | lg
    fullWidth = false,
    className = '',
    ...props
}) => {
    const variants = {
        primary: {
            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            color: 'white',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
        },
        secondary: {
            background: 'var(--color-bg-elevated)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border)'
        },
        danger: {
            background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
            color: 'white',
            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
        }
    }

    const sizes = {
        sm: 'px-3 py-2 text-xs min-h-[36px]',
        md: 'px-4 py-2.5 text-sm min-h-[44px]',
        lg: 'px-6 py-3 text-base min-h-[52px]'
    }

    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            className={`
                ${sizes[size]}
                ${fullWidth ? 'w-full' : ''}
                rounded-xl font-medium
                flex items-center justify-center gap-2
                transition-all duration-200
                hover:-translate-y-0.5 active:translate-y-0
                disabled:opacity-60 disabled:transform-none disabled:cursor-not-allowed
                ${className}
            `}
            style={variants[variant]}
            {...props}
        >
            {loading ? (
                <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {loadingText}
                </>
            ) : (
                children
            )}
        </button>
    )
}

/**
 * Spinner component
 */
export const Spinner = ({ size = 'md', color = '#10B981', className = '' }) => {
    const sizes = {
        sm: 'w-4 h-4',
        md: 'w-6 h-6',
        lg: 'w-8 h-8',
        xl: 'w-12 h-12'
    }

    return (
        <Loader2
            className={`animate-spin ${sizes[size]} ${className}`}
            style={{ color }}
        />
    )
}

/**
 * Full page loader
 */
export const PageLoader = ({ message = 'Loading...' }) => (
    <div className="fixed inset-0 flex flex-col items-center justify-center z-50" style={{ background: 'var(--color-bg-primary)' }}>
        <div className="relative">
            <div
                className="absolute inset-0 rounded-full blur-xl animate-pulse"
                style={{ background: 'rgba(16, 185, 129, 0.3)' }}
            />
            <Spinner size="xl" className="relative" />
        </div>
        <p className="mt-4 text-sm font-medium" style={{ color: 'var(--color-text-muted)' }}>
            {message}
        </p>
    </div>
)

/**
 * Inline loader for content areas
 */
export const InlineLoader = ({ message = 'Loading...', className = '' }) => (
    <div className={`flex items-center justify-center gap-3 py-8 ${className}`}>
        <Spinner size="md" />
        <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {message}
        </span>
    </div>
)

/**
 * Shimmer effect for images
 */
export const ShimmerImage = ({ width, height, className = '' }) => (
    <div
        className={`overflow-hidden rounded-xl ${className}`}
        style={{
            width,
            height,
            background: 'var(--color-bg-secondary)'
        }}
    >
        <div
            className="w-full h-full"
            style={{
                background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%)',
                animation: 'shimmer 1.5s infinite'
            }}
        />
    </div>
)

// Add keyframes to document
if (typeof document !== 'undefined') {
    const style = document.createElement('style')
    style.textContent = `
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
    `
    if (!document.querySelector('#loading-keyframes')) {
        style.id = 'loading-keyframes'
        document.head.appendChild(style)
    }
}

export default {
    Skeleton,
    SkeletonText,
    SkeletonCard,
    SkeletonChatMessage,
    SkeletonProfile,
    SkeletonDashboard,
    TypingIndicator,
    LoadingButton,
    Spinner,
    PageLoader,
    InlineLoader,
    ShimmerImage
}
