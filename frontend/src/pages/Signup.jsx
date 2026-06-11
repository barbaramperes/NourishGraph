import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useGoogleLogin } from '@react-oauth/google'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import AuthLayout from '../components/AuthLayout'
import { Eye, EyeOff, Check, ArrowRight, Shield } from 'lucide-react'

export default function Signup() {
    const navigate = useNavigate()
    const { signup, loginWithGoogle } = useAuthStore()
    const { saveProfile, loadProfile, clearAllData } = useAppStore()

    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirm, setConfirm] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const getPasswordStrength = () => {
        let strength = 0
        if (password.length >= 8) strength++
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++
        if (password.match(/\d/)) strength++
        if (password.match(/[^a-zA-Z\d]/)) strength++
        return strength
    }

    const strength = getPasswordStrength()
    const strengthLabels = ['Weak', 'Fair', 'Good', 'Strong']
    const strengthColors = ['bg-red-500', 'bg-amber-500', 'bg-[#10B981]', 'bg-[#059669]']
    const strengthGlow = ['shadow-red-500/30', 'shadow-amber-500/30', 'shadow-[#10B981]/30', 'shadow-[#059669]/30']

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')

        if (password !== confirm) {
            setError('Passwords do not match')
            return
        }

        if (strength < 2) {
            setError('Please use a stronger password')
            return
        }

        setLoading(true)

        // Clear any old user data before creating new account
        clearAllData()

        try {
            const result = await signup(email, password, name)

            if (result.success) {
                navigate('/onboarding')
            } else {
                setError(result.message || 'Error creating account. Please try again.')
            }
        } catch (err) {
            setError('Error creating account. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // Google Sign Up
    const googleSignup = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            setLoading(true)
            setError('')

            // Clear any old user data before creating new account
            clearAllData()

            try {
                const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                    headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
                })
                const userInfo = await res.json()

                // Google signup now uses backend API for proper database storage
                const result = await loginWithGoogle({
                    email: userInfo.email,
                    name: userInfo.name,
                    picture: userInfo.picture
                })

                if (result.success) {
                    navigate(result.needsOnboarding ? '/onboarding' : '/')
                } else {
                    setError(result.message || 'Failed to sign up with Google.')
                }
            } catch (err) {
                console.error('Google signup error:', err)
                setError('Failed to sign up with Google.')
            } finally {
                setLoading(false)
            }
        },
        onError: () => setError('Google sign-up failed.')
    })

    return (
        <AuthLayout>
            <div className="text-center mb-6 sm:mb-8">
                <h1 className="text-xl sm:text-2xl font-bold mb-2" style={{ background: 'var(--color-gradient-title)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Create your account
                </h1>
                <p className="text-xs sm:text-sm" style={{ color: 'var(--color-text-muted)' }}>Start your personalized nutrition journey</p>
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
                    <label className="text-xs sm:text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Full Name</label>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="John Doe"
                        required
                        className="w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-accent/10 transition-all duration-300"
                        style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                    />
                </div>

                <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Email</label>
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
                            minLength={8}
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

                    {/* Password strength indicator */}
                    {password && (
                        <div className="space-y-2.5 mt-3">
                            <div className="flex gap-1.5">
                                {[0, 1, 2, 3].map((i) => (
                                    <div
                                        key={i}
                                        className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${i < strength
                                            ? `${strengthColors[strength - 1]} shadow-lg ${strengthGlow[strength - 1]}`
                                            : ''
                                            }`}
                                        style={i >= strength ? { background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' } : {}}
                                    />
                                ))}
                            </div>
                            <div className="flex items-center justify-between">
                                <p className={`text-xs font-medium ${strength >= 3 ? 'text-emerald-400' : strength >= 2 ? 'text-blue-400' : ''}`} style={strength < 2 ? { color: 'var(--color-text-muted)' } : {}}>
                                    {strength > 0 ? strengthLabels[strength - 1] : 'Use at least 8 characters'}
                                </p>
                                {strength >= 3 && (
                                    <div className="flex items-center gap-1 text-xs" style={{ color: '#10B981' }}>
                                        <Shield className="w-3 h-3" />
                                        <span>Secure</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Confirm Password</label>
                    <input
                        type="password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        placeholder="••••••••"
                        required
                        className={`w-full px-3 sm:px-4 py-3 sm:py-3.5 rounded-lg sm:rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 transition-all duration-300 ${confirm && password !== confirm
                            ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
                            : confirm && password === confirm
                                ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500/20'
                                : 'focus:ring-accent/10'
                            }`}
                        style={{ background: 'var(--color-input-bg)', border: `1px solid ${confirm && password !== confirm ? 'rgba(239, 68, 68, 0.5)' : confirm && password === confirm ? 'rgba(16, 185, 129, 0.5)' : 'var(--color-input-border)'}`, color: 'var(--color-text-primary)' }}
                    />
                    {confirm && password !== confirm && (
                        <p className="text-xs text-red-400 flex items-center gap-1 mt-1">
                            <span>✕</span> Passwords don't match
                        </p>
                    )}
                    {confirm && password === confirm && (
                        <p className="text-xs flex items-center gap-1 mt-1" style={{ color: '#10B981' }}>
                            <Check className="w-3 h-3" /> Passwords match
                        </p>
                    )}
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className="relative w-full py-3 sm:py-3.5 text-white text-sm sm:text-base font-semibold rounded-lg sm:rounded-xl overflow-hidden group disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-300 shadow-lg"
                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)' }}
                >
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{ background: 'linear-gradient(135deg, #059669 0%, #047857 100%)' }} />
                    <div className="relative flex items-center justify-center gap-2">
                        {loading ? (
                            <>
                                <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                <span>Creating account...</span>
                            </>
                        ) : (
                            <>
                                <span>Create Account</span>
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
                        onClick={() => googleSignup()}
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
                Already have an account?{' '}
                <Link to="/login" className="font-medium transition-colors" style={{ color: '#10B981' }}>
                    Sign in
                </Link>
            </p>
        </AuthLayout>
    )
}
