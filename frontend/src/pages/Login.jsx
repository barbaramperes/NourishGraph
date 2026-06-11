import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useGoogleLogin } from '@react-oauth/google'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import AuthLayout from '../components/AuthLayout'
import { Eye, EyeOff, ArrowRight, Sparkles, X, Mail, Check, Loader2 } from 'lucide-react'

// API base URL
const API_BASE = import.meta.env.PROD ? '' : '/api'

/**
 * Forgot Password Modal
 */
const ForgotPasswordModal = ({ isOpen, onClose }) => {
    const [email, setEmail] = useState('')
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const response = await fetch(`${API_BASE}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            })

            const data = await response.json()

            if (data.success) {
                setSuccess(true)
            } else {
                setError(data.message || 'Something went wrong')
            }
        } catch (err) {
            setError('Failed to send reset email. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleClose = () => {
        setEmail('')
        setSuccess(false)
        setError('')
        onClose()
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div
                className="w-full max-w-md rounded-2xl overflow-hidden animate-fadeIn"
                style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}
            >
                {/* Header */}
                <div className="p-6 pb-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div
                                className="w-10 h-10 rounded-xl flex items-center justify-center"
                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
                            >
                                <Mail className="w-5 h-5 text-white" />
                            </div>
                            <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                Reset Password
                            </h3>
                        </div>
                        <button
                            onClick={handleClose}
                            className="p-2 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    {success ? (
                        <div className="text-center py-4">
                            <div
                                className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                                style={{ background: 'rgba(16, 185, 129, 0.15)' }}
                            >
                                <Check className="w-8 h-8" style={{ color: '#10B981' }} />
                            </div>
                            <h4 className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                                Check your email
                            </h4>
                            <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
                                If an account exists with <strong>{email}</strong>, you'll receive password reset instructions shortly.
                            </p>
                            <button
                                onClick={handleClose}
                                className="w-full py-3 rounded-xl text-white font-medium transition-all hover:-translate-y-0.5"
                                style={{
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                Back to Login
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit}>
                            <p className="text-sm mb-4" style={{ color: 'var(--color-text-muted)' }}>
                                Enter your email address and we'll send you instructions to reset your password.
                            </p>

                            {error && (
                                <div
                                    className="mb-4 px-4 py-3 rounded-lg text-sm"
                                    style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}
                                >
                                    {error}
                                </div>
                            )}

                            <div className="mb-4">
                                <label className="block text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                                    Email address
                                </label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="your@email.com"
                                    required
                                    className="w-full px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400/50 transition-all"
                                    style={{
                                        background: 'var(--color-input-bg)',
                                        border: '1px solid var(--color-input-border)',
                                        color: 'var(--color-text-primary)'
                                    }}
                                />
                            </div>

                            <div className="flex gap-3">
                                <button
                                    type="button"
                                    onClick={handleClose}
                                    className="flex-1 py-3 rounded-xl font-medium transition-all hover:-translate-y-0.5"
                                    style={{
                                        background: 'var(--color-input-bg)',
                                        border: '1px solid var(--color-input-border)',
                                        color: 'var(--color-text-secondary)'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading || !email}
                                    className="flex-1 py-3 rounded-xl text-white font-medium transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none flex items-center justify-center gap-2"
                                    style={{
                                        background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                        boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                                    }}
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Sending...
                                        </>
                                    ) : (
                                        'Send Reset Link'
                                    )}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    )
}

export default function Login() {
    const navigate = useNavigate()
    const { login, loginWithGoogle } = useAuthStore()
    const { loadProfile, saveProfile, clearAllData, profile } = useAppStore()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [showForgotPassword, setShowForgotPassword] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const result = await login(email, password)

            if (result.success) {
                // Clear cached app data (keeps auth)
                clearAllData()
                navigate(result.needsOnboarding ? '/onboarding' : '/')
            } else {
                setError(result.message || 'Invalid credentials. Please try again.')
            }
        } catch (err) {
            setError('Invalid credentials. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // Google Login
    const googleLogin = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            setLoading(true)
            setError('')

            try {
                const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                    headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
                })
                const userInfo = await res.json()

                // Google login now uses backend API for proper database verification
                const result = await loginWithGoogle({
                    email: userInfo.email,
                    name: userInfo.name,
                    picture: userInfo.picture
                })

                if (result.success) {
                    // Clear cached app data (keeps auth)
                    clearAllData()
                    navigate(result.needsOnboarding ? '/onboarding' : '/')
                } else {
                    setError(result.message || 'Failed to sign in with Google.')
                }
            } catch (err) {
                console.error('Google login error:', err)
                setError('Failed to sign in with Google.')
            } finally {
                setLoading(false)
            }
        },
        onError: () => setError('Google sign-in failed.')
    })

    return (
        <AuthLayout>
            <div className="text-center mb-6 sm:mb-8">
                <h1 className="text-xl sm:text-2xl font-bold mb-2" style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Welcome back
                </h1>
                <p className="text-xs sm:text-sm" style={{ color: 'var(--color-text-muted)' }}>Sign in to continue your nutrition journey</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
                {error && (
                    <div className="p-3 sm:p-4 bg-red-500/10 border border-red-500/20 rounded-lg sm:rounded-xl text-red-400 text-xs sm:text-sm flex items-center gap-2 sm:gap-3">
                        <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-red-500/20 flex items-center justify-center shrink-0">
                            <span className="text-red-400 text-sm">!</span>
                        </div>
                        {error}
                    </div>
                )}

                <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium flex items-center gap-2" style={{ color: 'var(--color-text-secondary)' }}>
                        Email
                    </label>
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="your@email.com"
                        required
                        className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-accent/10 transition-all duration-300"
                        style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                    />
                </div>

                <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Password</label>
                    <div className="relative group">
                        <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                            minLength={6}
                            className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-accent/10 transition-all duration-300 pr-10 sm:pr-12"
                            style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 transition-colors"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            {showPassword ? <EyeOff size={16} className="sm:w-[18px] sm:h-[18px]" /> : <Eye size={16} className="sm:w-[18px] sm:h-[18px]" />}
                        </button>
                    </div>
                </div>

                {/* Forgot password link */}
                <div className="text-right">
                    <button
                        type="button"
                        onClick={() => setShowForgotPassword(true)}
                        className="text-xs sm:text-sm transition-colors hover:underline"
                        style={{ color: '#10B981' }}
                    >
                        Forgot password?
                    </button>
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className="relative w-full py-3 sm:py-4 text-white text-sm sm:text-base font-semibold rounded-lg sm:rounded-xl overflow-hidden group disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-300 shadow-lg"
                    style={{
                        background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                        boxShadow: '0 8px 30px rgba(16, 185, 129, 0.3), inset 0 1px 0 rgba(255,255,255,0.15)'
                    }}
                >
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                        style={{ background: 'linear-gradient(135deg, #059669 0%, #10B981 100%)' }} />
                    <div className="relative flex items-center justify-center gap-2">
                        {loading ? (
                            <>
                                <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>Signing in...</span>
                            </>
                        ) : (
                            <>
                                <span>Sign In</span>
                                <ArrowRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 group-hover:translate-x-1 transition-transform" />
                            </>
                        )}
                    </div>
                </button>
            </form>

            <div className="mt-6 sm:mt-8">
                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                    </div>
                    <div className="relative flex justify-center">
                        <span className="px-4 bg-transparent text-[10px] sm:text-xs uppercase tracking-widest backdrop-blur-xl" style={{ color: 'var(--color-text-muted)' }}>
                            or continue with
                        </span>
                    </div>
                </div>

                <div className="mt-4 sm:mt-6">
                    <button
                        type="button"
                        onClick={() => googleLogin()}
                        disabled={loading}
                        className="w-full flex items-center justify-center gap-2 py-2.5 sm:py-3 rounded-lg sm:rounded-xl transition-all duration-300 disabled:opacity-50 group"
                        style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                    >
                        <svg className="w-4 h-4 sm:w-5 sm:h-5" viewBox="0 0 24 24">
                            <path fill="#EA4335" d="M5.26620003,9.76452941 C6.19878754,6.93863203 8.85444915,4.90909091 12,4.90909091 C13.6909091,4.90909091 15.2181818,5.50909091 16.4181818,6.49090909 L19.9090909,3 C17.7818182,1.14545455 15.0545455,0 12,0 C7.27006974,0 3.1977497,2.69829785 1.23999023,6.65002441 L5.26620003,9.76452941 Z" />
                            <path fill="#34A853" d="M16.0407269,18.0125889 C14.9509167,18.7163016 13.5660892,19.0909091 12,19.0909091 C8.86648613,19.0909091 6.21911939,17.076871 5.27698177,14.2678769 L1.23746264,17.3349879 C3.19279051,21.2936293 7.26500293,24 12,24 C14.9328362,24 17.7353462,22.9573905 19.834192,20.9995801 L16.0407269,18.0125889 Z" />
                            <path fill="#4A90E2" d="M19.834192,20.9995801 C22.0291676,18.9520994 23.4545455,15.903663 23.4545455,12 C23.4545455,11.2909091 23.3454545,10.5272727 23.1818182,9.81818182 L12,9.81818182 L12,14.4545455 L18.4363636,14.4545455 C18.1187732,16.013626 17.2662994,17.2212117 16.0407269,18.0125889 L19.834192,20.9995801 Z" />
                            <path fill="#FBBC05" d="M5.27698177,14.2678769 C5.03832634,13.556323 4.90909091,12.7937589 4.90909091,12 C4.90909091,11.2182781 5.03443647,10.4668121 5.26620003,9.76452941 L1.23999023,6.65002441 C0.43658717,8.26043162 0,10.0753848 0,12 C0,13.9195484 0.444780743,15.7301709 1.24,17.3349879 L5.27698177,14.2678769 Z" />
                        </svg>
                        <span className="text-xs sm:text-sm font-medium">Continue with Google</span>
                    </button>
                </div>
            </div>

            <p className="mt-6 sm:mt-8 text-center text-xs sm:text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Don't have an account?{' '}
                <Link to="/signup" className="font-medium transition-colors" style={{ color: '#10B981' }}>
                    Create one
                </Link>
            </p>

            {/* Forgot Password Modal */}
            <ForgotPasswordModal
                isOpen={showForgotPassword}
                onClose={() => setShowForgotPassword(false)}
            />
        </AuthLayout>
    )
}
