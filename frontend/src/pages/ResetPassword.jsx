import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import { Eye, EyeOff, ArrowRight, Check, X, Loader2, AlertCircle, KeyRound } from 'lucide-react'

// API base URL
const API_BASE = import.meta.env.PROD ? '' : '/api'

export default function ResetPassword() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    const token = searchParams.get('token')
    
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)
    const [error, setError] = useState('')
    const [tokenError, setTokenError] = useState(false)

    // Validate token presence
    useEffect(() => {
        if (!token) {
            setTokenError(true)
        }
    }, [token])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')

        // Validate passwords match
        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return
        }

        // Validate password length
        if (password.length < 6) {
            setError('Password must be at least 6 characters long')
            return
        }

        setLoading(true)

        try {
            const response = await fetch(`${API_BASE}/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    token,
                    new_password: password 
                })
            })

            const data = await response.json()

            if (response.ok && data.success) {
                setSuccess(true)
            } else {
                if (response.status === 400) {
                    setTokenError(true)
                    setError(data.detail || 'Invalid or expired reset link')
                } else {
                    setError(data.detail || data.message || 'Failed to reset password')
                }
            }
        } catch (err) {
            setError('Failed to reset password. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // If no token provided
    if (tokenError) {
        return (
            <AuthLayout
                title="Invalid Reset Link"
                subtitle="This password reset link is invalid or has expired"
            >
                <div className="text-center py-8">
                    <div 
                        className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
                        style={{ background: 'rgba(239, 68, 68, 0.15)' }}
                    >
                        <X className="w-10 h-10" style={{ color: '#EF4444' }} />
                    </div>
                    
                    <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                        Link Expired or Invalid
                    </h3>
                    
                    <p className="mb-6" style={{ color: 'var(--color-text-muted)' }}>
                        This password reset link may have expired or already been used. 
                        Please request a new password reset.
                    </p>

                    <Link
                        to="/login"
                        className="inline-flex items-center justify-center gap-2 w-full py-3 rounded-xl font-medium transition-all"
                        style={{ 
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                            color: 'white'
                        }}
                    >
                        Return to Login
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </AuthLayout>
        )
    }

    // Success state
    if (success) {
        return (
            <AuthLayout
                title="Password Reset!"
                subtitle="Your password has been successfully updated"
            >
                <div className="text-center py-8">
                    <div 
                        className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
                        style={{ background: 'rgba(16, 185, 129, 0.15)' }}
                    >
                        <Check className="w-10 h-10" style={{ color: '#10B981' }} />
                    </div>
                    
                    <h3 className="text-xl font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                        Success!
                    </h3>
                    
                    <p className="mb-6" style={{ color: 'var(--color-text-muted)' }}>
                        Your password has been reset successfully. 
                        You can now log in with your new password.
                    </p>

                    <Link
                        to="/login"
                        className="inline-flex items-center justify-center gap-2 w-full py-3 rounded-xl font-medium transition-all"
                        style={{ 
                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                            color: 'white'
                        }}
                    >
                        Go to Login
                        <ArrowRight className="w-4 h-4" />
                    </Link>
                </div>
            </AuthLayout>
        )
    }

    return (
        <AuthLayout
            title="Create New Password"
            subtitle="Enter your new password below"
        >
            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Icon */}
                <div className="flex justify-center mb-2">
                    <div 
                        className="w-16 h-16 rounded-2xl flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
                    >
                        <KeyRound className="w-8 h-8 text-white" />
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div 
                        className="p-4 rounded-xl flex items-center gap-3"
                        style={{ 
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.2)'
                        }}
                    >
                        <AlertCircle className="w-5 h-5 flex-shrink-0" style={{ color: '#EF4444' }} />
                        <span className="text-sm" style={{ color: '#EF4444' }}>{error}</span>
                    </div>
                )}

                {/* New Password */}
                <div className="space-y-2">
                    <label 
                        htmlFor="password" 
                        className="block text-sm font-medium"
                        style={{ color: 'var(--color-text-secondary)' }}
                    >
                        New Password
                    </label>
                    <div className="relative">
                        <input
                            id="password"
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl pr-12 focus:outline-none focus:ring-2 transition-all"
                            style={{
                                background: 'var(--color-bg-tertiary)',
                                border: '1px solid var(--color-border)',
                                color: 'var(--color-text-primary)',
                                '--tw-ring-color': '#10B981'
                            }}
                            placeholder="Enter new password"
                            required
                            minLength={6}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                    </div>
                </div>

                {/* Confirm Password */}
                <div className="space-y-2">
                    <label 
                        htmlFor="confirmPassword" 
                        className="block text-sm font-medium"
                        style={{ color: 'var(--color-text-secondary)' }}
                    >
                        Confirm New Password
                    </label>
                    <div className="relative">
                        <input
                            id="confirmPassword"
                            type={showConfirmPassword ? 'text' : 'password'}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl pr-12 focus:outline-none focus:ring-2 transition-all"
                            style={{
                                background: 'var(--color-bg-tertiary)',
                                border: '1px solid var(--color-border)',
                                color: 'var(--color-text-primary)',
                                '--tw-ring-color': '#10B981'
                            }}
                            placeholder="Confirm new password"
                            required
                            minLength={6}
                        />
                        <button
                            type="button"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                    </div>
                </div>

                {/* Password Requirements */}
                <div className="text-xs space-y-1" style={{ color: 'var(--color-text-muted)' }}>
                    <p className="flex items-center gap-2">
                        <span className={password.length >= 6 ? 'text-green-500' : ''}>
                            {password.length >= 6 ? '✓' : '○'}
                        </span>
                        At least 6 characters
                    </p>
                    <p className="flex items-center gap-2">
                        <span className={password && password === confirmPassword ? 'text-green-500' : ''}>
                            {password && password === confirmPassword ? '✓' : '○'}
                        </span>
                        Passwords match
                    </p>
                </div>

                {/* Submit Button */}
                <button
                    type="submit"
                    disabled={loading || password.length < 6 || password !== confirmPassword}
                    className="w-full py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ 
                        background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                        color: 'white'
                    }}
                >
                    {loading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Resetting Password...
                        </>
                    ) : (
                        <>
                            Reset Password
                            <ArrowRight className="w-4 h-4" />
                        </>
                    )}
                </button>

                {/* Back to Login */}
                <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
                    Remember your password?{' '}
                    <Link 
                        to="/login" 
                        className="font-medium hover:underline"
                        style={{ color: '#10B981' }}
                    >
                        Back to Login
                    </Link>
                </p>
            </form>
        </AuthLayout>
    )
}
