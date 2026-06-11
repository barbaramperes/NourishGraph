/**
 * Profile Page - Professional profile management
 *
 * Uses reusable ProfileForm component
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import { ProfileForm } from '../components/profile/ProfileForm'
import { SkeletonProfile } from '../components/ui/LoadingStates'
import {
    User,
    ArrowLeft,
    Lock,
    Eye,
    EyeOff,
    Check,
    Shield,
    ChevronDown,
    ChevronUp
} from 'lucide-react'

/**
 * Password Change Section Component
 */
const PasswordSection = () => {
    const [isExpanded, setIsExpanded] = useState(false)
    const [showCurrentPassword, setShowCurrentPassword] = useState(false)
    const [showNewPassword, setShowNewPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [form, setForm] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    })

    const handleChange = async () => {
        setError('')
        setSuccess(false)

        if (form.newPassword !== form.confirmPassword) {
            setError('New passwords do not match')
            return
        }
        if (form.newPassword.length < 6) {
            setError('Password must be at least 6 characters')
            return
        }

        setLoading(true)
        try {
            const token = localStorage.getItem('nourishgraph-token')
            const apiBase = import.meta.env.PROD ? '' : '/api'
            const response = await fetch(`${apiBase}/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    current_password: form.currentPassword,
                    new_password: form.newPassword
                })
            })

            if (response.ok) {
                setSuccess(true)
                setForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
                setTimeout(() => {
                    setIsExpanded(false)
                    setSuccess(false)
                }, 2000)
            } else {
                const data = await response.json()
                setError(data.detail || 'Failed to change password')
            }
        } catch (err) {
            setError('Failed to change password')
        } finally {
            setLoading(false)
        }
    }

    const PasswordInput = ({ label, value, onChange, show, onToggleShow }) => (
        <div className="space-y-1.5">
            <label className="text-xs sm:text-sm" style={{ color: 'var(--color-text-muted)' }}>
                {label}
            </label>
            <div className="relative">
                <input
                    type={show ? 'text' : 'password'}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full px-3 sm:px-4 py-2.5 sm:py-3 pr-10 rounded-xl text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-red-400/50 transition-all"
                    style={{
                        background: 'var(--color-input-bg)',
                        border: '1px solid var(--color-input-border)',
                        color: 'var(--color-input-text)'
                    }}
                />
                <button
                    type="button"
                    onClick={onToggleShow}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
                    style={{ color: 'var(--color-text-muted)' }}
                >
                    {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
            </div>
        </div>
    )

    return (
        <div
            className="rounded-xl overflow-hidden"
            style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)'
            }}
        >
            {/* Header */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full p-4 flex items-center justify-between hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{
                            background: '#EF4444',
                            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                        }}
                    >
                        <Shield className="w-5 h-5" style={{ color: '#ffffff' }} />
                    </div>
                    <div className="text-left">
                        <div className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                            Security Settings
                        </div>
                        <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            Change your password
                        </div>
                    </div>
                </div>
                {isExpanded ? (
                    <ChevronUp className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                ) : (
                    <ChevronDown className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                )}
            </button>

            {/* Expanded content */}
            {isExpanded && (
                <div
                    className="p-4 space-y-4 animate-fadeIn"
                    style={{ borderTop: '1px solid var(--color-border)' }}
                >
                    <PasswordInput
                        label="Current Password"
                        value={form.currentPassword}
                        onChange={(v) => setForm(f => ({ ...f, currentPassword: v }))}
                        show={showCurrentPassword}
                        onToggleShow={() => setShowCurrentPassword(!showCurrentPassword)}
                    />
                    <PasswordInput
                        label="New Password"
                        value={form.newPassword}
                        onChange={(v) => setForm(f => ({ ...f, newPassword: v }))}
                        show={showNewPassword}
                        onToggleShow={() => setShowNewPassword(!showNewPassword)}
                    />
                    <PasswordInput
                        label="Confirm New Password"
                        value={form.confirmPassword}
                        onChange={(v) => setForm(f => ({ ...f, confirmPassword: v }))}
                        show={showConfirmPassword}
                        onToggleShow={() => setShowConfirmPassword(!showConfirmPassword)}
                    />

                    {/* Error/Success messages */}
                    {error && (
                        <p className="text-xs sm:text-sm" style={{ color: '#EF4444' }}>{error}</p>
                    )}
                    {success && (
                        <p className="text-xs sm:text-sm flex items-center gap-1" style={{ color: '#22C55E' }}>
                            <Check className="w-4 h-4" />
                            Password changed successfully!
                        </p>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                        <button
                            onClick={() => {
                                setIsExpanded(false)
                                setForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
                                setError('')
                            }}
                            className="flex-1 py-3 rounded-xl text-sm font-medium transition-all hover:-translate-y-0.5"
                            style={{
                                background: 'var(--color-input-bg)',
                                border: '1px solid var(--color-input-border)',
                                color: 'var(--color-text-secondary)'
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleChange}
                            disabled={loading || !form.currentPassword || !form.newPassword || !form.confirmPassword}
                            className="flex-1 py-3 rounded-xl text-sm font-medium text-white transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none flex items-center justify-center gap-2"
                            style={{
                                background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                                boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                            }}
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Updating...
                                </>
                            ) : (
                                <>
                                    <Lock className="w-4 h-4" />
                                    Update Password
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

/**
 * Main Profile Page
 */
export default function Profile() {
    const navigate = useNavigate()
    const { user, updateUser } = useAuthStore()
    const { profile, saveProfile, loadProfile, profileLoading } = useAppStore()
    const [isLoading, setIsLoading] = useState(true)

    // Load profile on mount
    useEffect(() => {
        const load = async () => {
            if (!profile?.name) {
                await loadProfile()
            }
            setIsLoading(false)
        }
        load()
    }, [loadProfile, profile?.name])

    // Prepare initial data for form
    const initialData = profile ? {
        name: profile.name || user?.name || '',
        email: profile.email || user?.email || '',
        age: profile.age || '',
        gender: profile.gender || profile.sex || '',
        weight: profile.weight || '',
        height: profile.height || '',
        goal: profile.goal || '',
        activity: profile.activity || 'moderate',
        diet: profile.diet || '',  // Use diet field directly
        allergies: Array.isArray(profile.allergies) ? profile.allergies : []
    } : {}

    const handleSave = async (formData) => {
        const savedProfile = await saveProfile({
            ...formData,
            diet: formData.diet || '',  // Ensure diet is saved
            restrictions: formData.diet ? [formData.diet] : [],
        })

        // Update auth store
        updateUser({ name: formData.name, email: formData.email })

        // Navigate back after save
        setTimeout(() => navigate('/'), 1500)

        return savedProfile
    }

    return (
        <div className="animate-fadeIn max-w-2xl mx-auto">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <button
                    onClick={() => navigate(-1)}
                    className="p-2.5 rounded-xl transition-all hover:-translate-x-1 min-w-[44px] min-h-[44px] flex items-center justify-center"
                    style={{
                        background: 'var(--color-bg-card)',
                        border: '1px solid var(--color-input-border)'
                    }}
                >
                    <ArrowLeft className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                </button>
                <div>
                    <div className="flex items-center gap-3">
                        <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
                        >
                            <User className="w-5 h-5" style={{ color: '#ffffff' }} />
                        </div>
                        <h1 className="text-xl sm:text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                            My Profile
                        </h1>
                    </div>
                    <p className="text-xs sm:text-sm mt-1 ml-[52px]" style={{ color: 'var(--color-text-muted)' }}>
                        Manage your personal information
                    </p>
                </div>
            </div>

            {isLoading || profileLoading ? (
                <div className="space-y-4">
                    <SkeletonProfile />
                </div>
            ) : (
                <div className="space-y-4">
                    {/* Profile Form Card */}
                    <div
                        className="rounded-xl overflow-hidden"
                        style={{
                            background: 'var(--color-bg-elevated)',
                            border: '1px solid var(--color-border)'
                        }}
                    >
                        <div
                            className="p-4"
                            style={{
                                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%)',
                                borderBottom: '1px solid var(--color-border)'
                            }}
                        >
                            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                Edit Profile
                            </h2>
                            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                                Update your information for personalized recommendations
                            </p>
                        </div>

                        <div className="p-4">
                            <ProfileForm
                                initialData={initialData}
                                onSave={handleSave}
                            />
                        </div>
                    </div>

                    {/* Password Section */}
                    <PasswordSection />
                </div>
            )}
        </div>
    )
}
