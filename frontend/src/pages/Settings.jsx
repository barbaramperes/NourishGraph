import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import {
    ArrowLeft, Trash2, Sun, Moon, Settings as SettingsIcon, Info, Heart, GraduationCap, Leaf, Shield
} from 'lucide-react'

export default function Settings() {
    const navigate = useNavigate()
    const { logout } = useAuthStore()
    const { clearAllData, theme, toggleTheme } = useAppStore()

    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
    const [deleteInput, setDeleteInput] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)

    const handleDeleteAccount = async () => {
        if (deleteInput !== 'DELETE') return

        setIsDeleting(true)
        try {
            // Get token from localStorage (same as other API calls)
            const token = localStorage.getItem('nourishgraph-token')

            // Delete account from database
            const apiBase = import.meta.env.PROD ? '' : '/api'
            const response = await fetch(`${apiBase}/account`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })

            if (response.ok) {
                // Clear local data and logout
                clearAllData?.()
                logout()
                navigate('/login')
            } else {
                const error = await response.json()
                alert(`Error deleting account: ${error.detail || 'Unknown error'}`)
            }
        } catch (error) {
            console.error('Delete account error:', error)
            alert('Failed to delete account. Please try again.')
        } finally {
            setIsDeleting(false)
        }
    }

    return (
        <div className="animate-fadeIn">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <button
                    onClick={() => navigate(-1)}
                    className="p-2.5 rounded-xl transition-all hover:-translate-x-1"
                    style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-input-border)' }}
                >
                    <ArrowLeft className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                </button>
                <div>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}>
                            <SettingsIcon className="w-5 h-5" style={{ color: '#ffffff' }} />
                        </div>
                        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>Settings</h1>
                    </div>
                    <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>Manage your preferences</p>
                </div>
            </div>

            <div className="space-y-6">
                {/* Appearance */}
                <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-input-border)' }}>
                    <div className="px-5 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid var(--color-input-border)' }}>
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: theme === 'dark' ? 'rgba(59,130,246,0.1)' : 'rgba(245,158,11,0.1)' }}>
                            {theme === 'dark' ? <Moon className="w-4 h-4 text-blue-500" /> : <Sun className="w-4 h-4 text-amber-500" />}
                        </div>
                        <h2 className="font-medium" style={{ color: 'var(--color-text-primary)' }}>Appearance</h2>
                    </div>
                    <div className="p-5">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Theme</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                                    {theme === 'dark' ? 'Dark mode enabled' : 'Light mode enabled'}
                                </p>
                            </div>
                            <button
                                onClick={toggleTheme}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg transition-all"
                                style={{
                                    background: theme === 'dark' ? 'var(--color-bg-elevated)' : 'var(--color-bg-hover)',
                                    border: '1px solid var(--color-input-border)'
                                }}
                            >
                                {theme === 'dark' ? (
                                    <>
                                        <Moon className="w-4 h-4" style={{ color: 'var(--color-primary)' }} />
                                        <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Dark</span>
                                    </>
                                ) : (
                                    <>
                                        <Sun className="w-4 h-4 text-yellow-500" />
                                        <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Light</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* About */}
                <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-input-border)' }}>
                    <div className="px-5 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid var(--color-input-border)' }}>
                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                            <Info className="w-4 h-4 text-blue-500" />
                        </div>
                        <h2 className="font-medium" style={{ color: 'var(--color-text-primary)' }}>About</h2>
                    </div>
                    <div className="p-5 space-y-4">
                        <div className="flex items-center gap-3">
                            <GraduationCap className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
                            <div>
                                <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Master's Thesis</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>NOVA Information Management School - NOVA IMS</p>
                            </div>
                        </div>
                        {/* Powered-by-AI block removed */}
                        <div className="flex items-center gap-3">
                            <Heart className="w-5 h-5 text-red-400" />
                            <div>
                                <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>Made with care</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>By Bárbara Peres © 2025</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Privacy & Data */}
                <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-input-border)' }}>
                    <div className="px-5 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid var(--color-input-border)' }}>
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                            <Shield className="w-4 h-4" style={{ color: 'var(--color-primary)' }} />
                        </div>
                        <h2 className="font-medium" style={{ color: 'var(--color-text-primary)' }}>Privacy & Data</h2>
                    </div>
                    <div className="p-2">
                        <Link
                            to="/privacy"
                            className="w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors"
                            style={{ color: 'var(--color-text-primary)' }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg-hover)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                            <div className="flex items-center gap-3">
                                <Shield className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                                <div>
                                    <p className="text-sm text-left">Privacy Policy</p>
                                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>How we protect your data</p>
                                </div>
                            </div>
                            <ArrowLeft className="w-4 h-4 rotate-180" style={{ color: 'var(--color-text-muted)' }} />
                        </Link>
                    </div>
                </div>

                {/* Danger Zone */}
                <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-bg-card)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                    <div className="px-5 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid rgba(239, 68, 68, 0.3)' }}>
                        <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                            <Trash2 className="w-4 h-4 text-red-500" />
                        </div>
                        <h2 className="font-medium text-red-400">Danger Zone</h2>
                    </div>
                    <div className="p-2">
                        <button
                            onClick={() => setShowDeleteConfirm(true)}
                            className="w-full flex items-center justify-between px-4 py-3 rounded-lg hover:bg-red-500/10 transition-colors"
                        >
                            <div>
                                <p className="text-sm text-red-400 text-left">Delete Account</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Permanently remove your account</p>
                            </div>
                            <Trash2 className="w-4 h-4 text-red-400" />
                        </button>
                    </div>
                </div>

                {/* App Info */}
                <div className="text-center py-6">
                    <div className="flex items-center justify-center gap-2 mb-2">
                        <Leaf className="w-4 h-4" style={{ color: 'var(--color-primary)' }} />
                        <span className="font-medium" style={{ color: 'var(--color-text-muted)' }}>NourishGraph</span>
                    </div>
                    <p className="text-xs" style={{ color: 'var(--color-text-subtle)' }}>Version 1.0.0</p>
                </div>
            </div>

            {/* Delete Account Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
                    <div className="w-full max-w-md rounded-2xl overflow-hidden" style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}>
                        <div className="p-6" style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <div className="w-14 h-14 rounded-2xl bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                                <Trash2 className="w-7 h-7 text-red-400" />
                            </div>
                            <h3 className="text-xl font-semibold text-center" style={{ color: 'var(--color-text-primary)' }}>Delete Account</h3>
                            <p className="text-sm text-center mt-2" style={{ color: 'var(--color-text-muted)' }}>
                                This action is permanent and cannot be undone.
                            </p>
                        </div>
                        <div className="p-6">
                            <label className="text-sm block mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                                Type <span className="text-red-400 font-mono">DELETE</span> to confirm
                            </label>
                            <input
                                type="text"
                                value={deleteInput}
                                onChange={(e) => setDeleteInput(e.target.value)}
                                placeholder="DELETE"
                                disabled={isDeleting}
                                className="w-full px-4 py-3 rounded-xl font-mono focus:outline-none focus:border-red-500/50"
                                style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-primary)' }}
                            />
                            <div className="flex gap-3 mt-6">
                                <button
                                    onClick={() => {
                                        setShowDeleteConfirm(false)
                                        setDeleteInput('')
                                    }}
                                    disabled={isDeleting}
                                    className="flex-1 py-3 px-4 rounded-xl font-medium transition-colors"
                                    style={{ background: 'var(--color-input-bg)', border: '1px solid var(--color-input-border)', color: 'var(--color-text-secondary)' }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleDeleteAccount}
                                    disabled={deleteInput !== 'DELETE' || isDeleting}
                                    className="flex-1 py-3 px-4 bg-red-500 rounded-xl text-white font-medium hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isDeleting ? 'Deleting...' : 'Delete'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
