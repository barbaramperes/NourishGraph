import React from 'react'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'

/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
            eventId: null
        }
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI
        return { hasError: true, error }
    }

    componentDidCatch(error, errorInfo) {
        // Log the error to console
        console.error('[ErrorBoundary] Caught error:', error)
        console.error('[ErrorBoundary] Error info:', errorInfo)

        this.setState({ errorInfo })

        // In production, you would send this to an error tracking service
        // Example: Sentry.captureException(error, { extra: errorInfo })
    }

    handleRefresh = () => {
        window.location.reload()
    }

    handleGoHome = () => {
        window.location.href = '/'
    }

    handleReportBug = () => {
        const { error, errorInfo } = this.state
        const errorDetails = `
Error: ${error?.toString()}
Component Stack: ${errorInfo?.componentStack}
URL: ${window.location.href}
Time: ${new Date().toISOString()}
User Agent: ${navigator.userAgent}
        `.trim()

        // Copy to clipboard
        navigator.clipboard.writeText(errorDetails).then(() => {
            alert('Error details copied to clipboard!')
        }).catch(() => {
            console.log('Error details:', errorDetails)
            alert('Check console for error details')
        })
    }

    render() {
        if (this.state.hasError) {
            const isDev = process.env.NODE_ENV === 'development'

            return (
                <div
                    className="min-h-screen flex items-center justify-center p-6"
                    style={{ background: 'var(--color-bg-primary, #0A0A0B)' }}
                >
                    <div
                        className="max-w-md w-full rounded-2xl p-8 text-center"
                        style={{
                            background: 'var(--color-bg-card, #1C1C1F)',
                            border: '1px solid var(--color-border, #333)'
                        }}
                    >
                        {/* Icon */}
                        <div
                            className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
                            style={{ background: 'rgba(239, 68, 68, 0.1)' }}
                        >
                            <AlertTriangle className="w-8 h-8 text-red-400" />
                        </div>

                        {/* Title */}
                        <h1
                            className="text-2xl font-bold mb-3"
                            style={{ color: 'var(--color-text-primary, #fff)' }}
                        >
                            Oops! Something went wrong
                        </h1>

                        {/* Description */}
                        <p
                            className="mb-6"
                            style={{ color: 'var(--color-text-muted, #888)' }}
                        >
                            We encountered an unexpected error. Don't worry, your data is safe.
                        </p>

                        {/* Error details (dev only) */}
                        {isDev && this.state.error && (
                            <div
                                className="mb-6 p-4 rounded-lg text-left overflow-auto max-h-40"
                                style={{
                                    background: 'var(--color-bg-elevated, #252529)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)'
                                }}
                            >
                                <p className="text-xs font-mono text-red-400 break-all">
                                    {this.state.error.toString()}
                                </p>
                                {this.state.errorInfo?.componentStack && (
                                    <pre className="text-xs font-mono text-gray-500 mt-2 whitespace-pre-wrap">
                                        {this.state.errorInfo.componentStack.slice(0, 500)}...
                                    </pre>
                                )}
                            </div>
                        )}

                        {/* Actions */}
                        <div className="flex flex-col sm:flex-row gap-3">
                            <button
                                onClick={this.handleRefresh}
                                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium text-white transition-all hover:opacity-90"
                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
                            >
                                <RefreshCw className="w-4 h-4" />
                                Refresh Page
                            </button>

                            <button
                                onClick={this.handleGoHome}
                                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-medium transition-all"
                                style={{
                                    background: 'var(--color-bg-elevated, #252529)',
                                    border: '1px solid var(--color-border, #333)',
                                    color: 'var(--color-text-secondary, #ccc)'
                                }}
                            >
                                <Home className="w-4 h-4" />
                                Go Home
                            </button>
                        </div>

                        {/* Report button */}
                        <button
                            onClick={this.handleReportBug}
                            className="mt-4 flex items-center justify-center gap-2 mx-auto text-sm transition-all hover:opacity-80"
                            style={{ color: 'var(--color-text-muted, #666)' }}
                        >
                            <Bug className="w-4 h-4" />
                            Copy error details
                        </button>

                        {/* Footer */}
                        <p
                            className="mt-6 text-xs"
                            style={{ color: 'var(--color-text-subtle, #555)' }}
                        >
                            If this problem persists, please contact support.
                        </p>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

export default ErrorBoundary
