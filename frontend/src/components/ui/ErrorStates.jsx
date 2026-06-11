/**
 * ErrorStates - Professional error handling components
 *
 * Includes:
 * - Friendly error messages (not technical jargon)
 * - Retry buttons
 * - Offline detection
 * - Error boundaries
 */

import { useState, useEffect, Component } from 'react'
import {
    AlertCircle,
    WifiOff,
    RefreshCw,
    Home,
    MessageSquare,
    ServerCrash,
    CloudOff,
    ShieldX,
    HelpCircle,
    ChevronDown,
    ChevronUp
} from 'lucide-react'
import { LoadingButton } from './LoadingStates'

/**
 * Error type configurations
 */
const ERROR_TYPES = {
    network: {
        icon: WifiOff,
        title: "Can't connect right now",
        message: "Please check your internet connection and try again.",
        color: '#F59E0B',
        suggestion: "Make sure you're connected to Wi-Fi or mobile data."
    },
    server: {
        icon: ServerCrash,
        title: "Something went wrong on our end",
        message: "We're having trouble processing your request.",
        color: '#EF4444',
        suggestion: "This is usually temporary. Please try again in a moment."
    },
    auth: {
        icon: ShieldX,
        title: "Session expired",
        message: "Please log in again to continue.",
        color: '#8B5CF6',
        suggestion: "Your session has timed out for security reasons."
    },
    notFound: {
        icon: HelpCircle,
        title: "Page not found",
        message: "The page you're looking for doesn't exist.",
        color: '#6B7280',
        suggestion: "Check the URL or go back to the home page."
    },
    offline: {
        icon: CloudOff,
        title: "You're offline",
        message: "Connect to the internet to continue using the app.",
        color: '#6B7280',
        suggestion: "Some features may still be available offline."
    },
    generic: {
        icon: AlertCircle,
        title: "Oops! Something went wrong",
        message: "We couldn't complete your request.",
        color: '#EF4444',
        suggestion: "Please try again. If the problem persists, contact support."
    }
}

/**
 * Main ErrorMessage component
 */
export const ErrorMessage = ({
    type = 'generic',
    title,
    message,
    suggestion,
    onRetry,
    onDismiss,
    retryText = 'Try again',
    showDetails = false,
    errorDetails,
    compact = false,
    className = ''
}) => {
    const [showErrorDetails, setShowErrorDetails] = useState(false)
    const [isRetrying, setIsRetrying] = useState(false)

    const config = ERROR_TYPES[type] || ERROR_TYPES.generic
    const Icon = config.icon

    const handleRetry = async () => {
        if (!onRetry) return
        setIsRetrying(true)
        try {
            await onRetry()
        } finally {
            setIsRetrying(false)
        }
    }

    if (compact) {
        return (
            <div
                className={`flex items-center gap-3 p-3 rounded-xl ${className}`}
                style={{
                    background: `${config.color}10`,
                    border: `1px solid ${config.color}30`
                }}
            >
                <Icon className="w-5 h-5 shrink-0" style={{ color: config.color }} />
                <span className="text-sm flex-1" style={{ color: config.color }}>
                    {title || config.title}
                </span>
                {onRetry && (
                    <button
                        onClick={handleRetry}
                        disabled={isRetrying}
                        className="p-1.5 rounded-lg transition-colors hover:bg-black/5"
                    >
                        <RefreshCw
                            className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`}
                            style={{ color: config.color }}
                        />
                    </button>
                )}
            </div>
        )
    }

    return (
        <div
            className={`rounded-xl overflow-hidden ${className}`}
            style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)'
            }}
        >
            {/* Icon header */}
            <div
                className="p-6 flex flex-col items-center text-center"
                style={{
                    background: `linear-gradient(180deg, ${config.color}15 0%, transparent 100%)`
                }}
            >
                <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                    style={{
                        background: `${config.color}20`,
                        boxShadow: `0 8px 24px ${config.color}20`
                    }}
                >
                    <Icon className="w-8 h-8" style={{ color: config.color }} />
                </div>

                <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                    {title || config.title}
                </h3>

                <p className="text-sm max-w-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    {message || config.message}
                </p>

                {(suggestion || config.suggestion) && (
                    <p className="text-xs mt-2 max-w-sm" style={{ color: 'var(--color-text-muted)' }}>
                        {suggestion || config.suggestion}
                    </p>
                )}
            </div>

            {/* Actions */}
            <div className="p-4 flex flex-col sm:flex-row gap-3" style={{ borderTop: '1px solid var(--color-border)' }}>
                {onRetry && (
                    <LoadingButton
                        onClick={handleRetry}
                        loading={isRetrying}
                        loadingText="Retrying..."
                        fullWidth
                    >
                        <RefreshCw className="w-4 h-4" />
                        {retryText}
                    </LoadingButton>
                )}

                {onDismiss && (
                    <LoadingButton
                        onClick={onDismiss}
                        variant="secondary"
                        fullWidth={!onRetry}
                    >
                        Dismiss
                    </LoadingButton>
                )}
            </div>

            {/* Technical details (collapsible) */}
            {showDetails && errorDetails && (
                <div style={{ borderTop: '1px solid var(--color-border)' }}>
                    <button
                        onClick={() => setShowErrorDetails(!showErrorDetails)}
                        className="w-full p-3 flex items-center justify-center gap-2 text-xs hover:bg-black/5 transition-colors"
                        style={{ color: 'var(--color-text-muted)' }}
                    >
                        {showErrorDetails ? 'Hide' : 'Show'} technical details
                        {showErrorDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {showErrorDetails && (
                        <div
                            className="p-3 font-mono text-xs overflow-auto max-h-32"
                            style={{
                                background: 'var(--color-bg-secondary)',
                                color: 'var(--color-text-muted)'
                            }}
                        >
                            {typeof errorDetails === 'string' ? errorDetails : JSON.stringify(errorDetails, null, 2)}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

/**
 * Inline error for form fields
 */
export const InlineError = ({ message, className = '' }) => {
    if (!message) return null

    return (
        <p
            className={`flex items-center gap-1.5 text-xs mt-1.5 ${className}`}
            style={{ color: '#EF4444' }}
        >
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            {message}
        </p>
    )
}

/**
 * Toast-style error notification
 */
export const ErrorToast = ({
    message,
    type = 'error',
    onDismiss,
    onRetry,
    autoHide = true,
    hideAfter = 5000,
    className = ''
}) => {
    useEffect(() => {
        if (autoHide && onDismiss) {
            const timer = setTimeout(onDismiss, hideAfter)
            return () => clearTimeout(timer)
        }
    }, [autoHide, hideAfter, onDismiss])

    const colors = {
        error: '#EF4444',
        warning: '#F59E0B',
        info: '#3B82F6'
    }

    const color = colors[type] || colors.error

    return (
        <div
            className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:max-w-sm z-50 animate-slideUp ${className}`}
        >
            <div
                className="p-4 rounded-xl shadow-2xl flex items-start gap-3"
                style={{
                    background: 'var(--color-bg-elevated)',
                    border: `1px solid ${color}30`,
                    boxShadow: `0 10px 40px ${color}20`
                }}
            >
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" style={{ color }} />

                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                        {message}
                    </p>

                    {onRetry && (
                        <button
                            onClick={onRetry}
                            className="text-xs font-medium mt-2 flex items-center gap-1 hover:underline"
                            style={{ color }}
                        >
                            <RefreshCw className="w-3 h-3" />
                            Try again
                        </button>
                    )}
                </div>

                {onDismiss && (
                    <button
                        onClick={onDismiss}
                        className="p-1 rounded-lg hover:bg-black/5 transition-colors"
                        style={{ color: 'var(--color-text-muted)' }}
                    >
                        <span className="sr-only">Dismiss</span>
                        ×
                    </button>
                )}
            </div>
        </div>
    )
}

/**
 * Offline indicator banner
 */
export const OfflineBanner = ({ className = '' }) => {
    const [isOffline, setIsOffline] = useState(!navigator.onLine)

    useEffect(() => {
        const handleOnline = () => setIsOffline(false)
        const handleOffline = () => setIsOffline(true)

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    if (!isOffline) return null

    return (
        <div
            className={`fixed top-0 left-0 right-0 z-50 px-4 py-2 flex items-center justify-center gap-2 text-sm font-medium ${className}`}
            style={{
                background: 'linear-gradient(135deg, #6B7280 0%, #4B5563 100%)',
                color: 'white'
            }}
        >
            <WifiOff className="w-4 h-4" />
            You're offline. Some features may be unavailable.
        </div>
    )
}

/**
 * Hook for offline detection
 */
export const useOnlineStatus = () => {
    const [isOnline, setIsOnline] = useState(navigator.onLine)

    useEffect(() => {
        const handleOnline = () => setIsOnline(true)
        const handleOffline = () => setIsOnline(false)

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    return isOnline
}

/**
 * Error Boundary Component
 */
export class ErrorBoundary extends Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, errorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo)
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null })
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback
            }

            return (
                <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--color-bg-primary)' }}>
                    <ErrorMessage
                        type="generic"
                        title="Something went wrong"
                        message="The app encountered an unexpected error."
                        onRetry={this.handleRetry}
                        showDetails={process.env.NODE_ENV === 'development'}
                        errorDetails={this.state.error?.message}
                    />
                </div>
            )
        }

        return this.props.children
    }
}

/**
 * Empty state component
 */
export const EmptyState = ({
    icon: Icon = MessageSquare,
    title = 'Nothing here yet',
    message = 'Get started by adding some content.',
    action,
    actionText = 'Get started',
    className = ''
}) => (
    <div className={`text-center py-12 px-4 ${className}`}>
        <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{
                background: 'var(--color-bg-secondary)',
                color: 'var(--color-text-muted)'
            }}
        >
            <Icon className="w-8 h-8" />
        </div>

        <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            {title}
        </h3>

        <p className="text-sm max-w-sm mx-auto mb-6" style={{ color: 'var(--color-text-muted)' }}>
            {message}
        </p>

        {action && (
            <LoadingButton onClick={action}>
                {actionText}
            </LoadingButton>
        )}
    </div>
)

// Add animation keyframes
if (typeof document !== 'undefined') {
    const style = document.createElement('style')
    style.textContent = `
        @keyframes slideUp {
            from { transform: translateY(100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .animate-slideUp {
            animation: slideUp 0.3s ease-out;
        }
    `
    if (!document.querySelector('#error-keyframes')) {
        style.id = 'error-keyframes'
        document.head.appendChild(style)
    }
}

export default {
    ErrorMessage,
    InlineError,
    ErrorToast,
    OfflineBanner,
    ErrorBoundary,
    EmptyState,
    useOnlineStatus
}
