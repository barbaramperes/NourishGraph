import { Link } from 'react-router-dom'
import { Home, ArrowLeft, Search, MessageSquare, User } from 'lucide-react'

/**
 * 404 Not Found Page
 * 
 * Displays a friendly error message when a route is not found.
 */
export default function NotFound() {
    return (
        <div
            className="min-h-screen flex items-center justify-center p-6"
            style={{ background: 'var(--color-bg-primary)' }}
        >
            <div className="max-w-lg w-full text-center">
                {/* 404 Illustration */}
                <div className="relative mb-8">
                    <div
                        className="text-[150px] sm:text-[200px] font-display font-bold leading-none select-none"
                        style={{
                            color: 'var(--color-primary)',
                            opacity: 0.1
                        }}
                    >
                        404
                    </div>
                    <div
                        className="absolute inset-0 flex items-center justify-center"
                    >
                        <div
                            className="w-24 h-24 rounded-full flex items-center justify-center"
                            style={{
                                background: 'var(--color-bg-card)',
                                border: '2px solid var(--color-border)'
                            }}
                        >
                            <Search
                                className="w-10 h-10"
                                style={{ color: 'var(--color-text-muted)' }}
                            />
                        </div>
                    </div>
                </div>

                {/* Error Message */}
                <h1
                    className="text-2xl sm:text-3xl font-display font-bold mb-3"
                    style={{ color: 'var(--color-text-primary)' }}
                >
                    Page Not Found
                </h1>
                <p
                    className="text-base sm:text-lg mb-8"
                    style={{ color: 'var(--color-text-secondary)' }}
                >
                    The page you're looking for doesn't exist or has been moved.
                </p>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                    <Link
                        to="/"
                        className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold text-white transition-all duration-300 hover:scale-105 hover:shadow-lg"
                        style={{
                            background: 'var(--gradient-primary)',
                            boxShadow: '0 4px 20px rgba(16, 185, 129, 0.3)'
                        }}
                    >
                        <Home className="w-4 h-4" />
                        Go to Dashboard
                    </Link>

                    <button
                        onClick={() => window.history.back()}
                        className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all duration-300 hover:scale-105"
                        style={{
                            background: 'var(--color-bg-card)',
                            color: 'var(--color-text-primary)',
                            border: '1px solid var(--color-border)'
                        }}
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Go Back
                    </button>
                </div>

                {/* Quick Links */}
                <div
                    className="mt-12 pt-8"
                    style={{ borderTop: '1px solid var(--color-border)' }}
                >
                    <p
                        className="text-sm mb-4"
                        style={{ color: 'var(--color-text-muted)' }}
                    >
                        Or try one of these:
                    </p>
                    <div className="flex flex-wrap justify-center gap-3">
                        <Link
                            to="/chat"
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-all duration-300 hover:scale-105"
                            style={{
                                background: 'var(--color-bg-card)',
                                color: 'var(--color-text-secondary)',
                                border: '1px solid var(--color-border)'
                            }}
                        >
                            <MessageSquare className="w-3.5 h-3.5" />
                            Chat with AI
                        </Link>

                        <Link
                            to="/profile"
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-all duration-300 hover:scale-105"
                            style={{
                                background: 'var(--color-bg-card)',
                                color: 'var(--color-text-secondary)',
                                border: '1px solid var(--color-border)'
                            }}
                        >
                            <User className="w-3.5 h-3.5" />
                            My Profile
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    )
}
