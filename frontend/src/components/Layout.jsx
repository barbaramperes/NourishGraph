import { Outlet, NavLink, useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { useAppStore } from '../stores/appStore'
import { useEffect, useState } from 'react'
import {
    LayoutDashboard,
    MessageCircle,
    LogOut,
    User,
    Sparkles,
    ChevronDown,
    Settings,
    Plus,
    Leaf,
    X,
    AlertTriangle,
    Zap
} from 'lucide-react'
import { ThemeToggle } from './ui/ThemeProvider'
import { OfflineBanner } from './ui/ErrorStates'

const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/chat', label: 'AI Chat', icon: MessageCircle },
]

export default function Layout() {
    const navigate = useNavigate()
    const { user, logout } = useAuthStore()
    const { profile, loadProfile, loadMeals, clearAllData } = useAppStore()
    const [showProfileMenu, setShowProfileMenu] = useState(false)
    const [showLogoutModal, setShowLogoutModal] = useState(false)

    // Load profile and meals only once on mount
    useEffect(() => {
        loadProfile()
        loadMeals()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Simple toggle for profile menu
    const toggleProfileMenu = () => {
        setShowProfileMenu(prev => !prev)
    }

    const closeProfileMenu = () => {
        setShowProfileMenu(false)
    }

    const handleLogout = () => {
        setShowLogoutModal(true)
        setShowProfileMenu(false)
    }

    const confirmLogout = () => {
        clearAllData()
        logout()
        navigate('/login')
    }

    const displayName = profile?.name || user?.name || 'User'
    const initial = displayName[0]?.toUpperCase() || '?'

    // Check if we're on chat page - no padding needed there
    const location = useLocation()
    const isChatPage = location.pathname === '/chat'

    return (
        <div className="flex flex-col overflow-hidden" style={{ background: 'var(--color-bg-primary)', height: '100dvh' }}>
            {/* Offline Banner */}
            <OfflineBanner />

            {/* Header */}
            <header className="sticky top-0 z-50" style={{ background: 'var(--color-bg-primary)', borderBottom: '1px solid var(--color-input-border)', backdropFilter: 'blur(12px)' }}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 sm:h-16 flex items-center justify-between gap-4 sm:gap-8">
                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-2.5 sm:gap-3 shrink-0 group">
                        <div className="relative">
                            {/* Hover glow */}
                            <div className="absolute -inset-2 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                style={{ background: 'radial-gradient(circle, rgba(16, 185, 129, 0.3) 0%, transparent 70%)', filter: 'blur(12px)' }} />

                            {/* Logo icon */}
                            <div className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-xl sm:rounded-xl flex items-center justify-center transform group-hover:scale-105 transition-all duration-300"
                                style={{
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 50%, #047857 100%)',
                                    boxShadow: '0 12px 30px rgba(16, 185, 129, 0.25), inset 0 1px 0 rgba(255,255,255,0.2)'
                                }}>
                                <Leaf className="w-5 h-5" style={{ color: '#ffffff' }} />
                            </div>
                        </div>

                        {/* Brand name */}
                        <div className="flex items-baseline gap-0">
                            <span className="text-lg sm:text-xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
                                Nourish
                            </span>
                            <span className="text-lg sm:text-xl font-bold tracking-tight"
                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                Graph
                            </span>
                        </div>
                    </Link>

                    {/* Navigation */}
                    <nav className="hidden md:flex items-center gap-1 px-2 py-1.5 rounded-full" style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', backdropFilter: 'blur(12px)' }}>
                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                end={item.path === '/'}
                                className={({ isActive }) =>
                                    `relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${isActive
                                        ? 'text-white'
                                        : 'hover:bg-black/5 dark:hover:bg-white/5'
                                    }`
                                }
                                style={({ isActive }) => isActive ? {
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                                } : { color: 'var(--color-text-secondary)' }}
                            >
                                {({ isActive }) => (
                                    <>
                                        <item.icon className="w-4 h-4" style={{ color: isActive ? '#ffffff' : 'var(--color-text-secondary)' }} />
                                        <span style={{ color: isActive ? '#ffffff' : 'var(--color-text-secondary)' }}>{item.label}</span>
                                    </>
                                )}
                            </NavLink>
                        ))}
                    </nav>

                    {/* Right Section */}
                    <div className="flex items-center gap-2 sm:gap-3">
                        {/* Theme Toggle */}
                        <ThemeToggle size="sm" />

                        {/* Profile Dropdown */}
                        <div className="relative">
                            <button
                                onClick={toggleProfileMenu}
                                className="flex items-center gap-2 sm:gap-3 py-1 sm:py-1.5 pl-1 sm:pl-1.5 pr-2 sm:pr-3 rounded-xl sm:rounded-2xl transition-all duration-200 group"
                                style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-input-border)' }}
                            >
                                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg sm:rounded-xl bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 flex items-center justify-center text-xs sm:text-sm font-bold shadow-lg shadow-emerald-500/25" style={{ color: '#ffffff' }}>
                                    {initial}
                                </div>
                                <div className="hidden sm:block text-left">
                                    <div className="text-sm font-semibold leading-tight" style={{ color: 'var(--color-text-primary)' }}>{displayName}</div>
                                </div>
                                <ChevronDown className={`w-3.5 h-3.5 sm:w-4 sm:h-4 transition-transform duration-200 ${showProfileMenu ? 'rotate-180' : ''}`} style={{ color: 'var(--color-text-muted)' }} />
                            </button>

                            {/* Dropdown Menu */}
                            {showProfileMenu && (
                                <>
                                    {/* Invisible overlay to close dropdown */}
                                    <div
                                        className="fixed inset-0 z-[199]"
                                        onClick={closeProfileMenu}
                                    />
                                    <div
                                        className="absolute right-0 top-full mt-2 w-56 z-[200] backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden"
                                        style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-input-border)' }}
                                    >
                                        <div className="p-3" style={{ borderBottom: '1px solid var(--color-input-border)' }}>
                                            <div className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>{displayName}</div>
                                            <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{profile?.email || user?.email || 'user@email.com'}</div>
                                        </div>
                                        <div className="p-2">
                                            <Link
                                                to="/profile"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-3 px-3 py-2.5 text-sm rounded-xl transition-colors hover:bg-emerald-500/10"
                                                style={{ color: 'var(--color-text-secondary)' }}
                                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-primary)'}
                                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-text-secondary)'}
                                            >
                                                <User className="w-4 h-4" />
                                                <span>My Profile</span>
                                            </Link>
                                            <Link
                                                to="/settings"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-3 px-3 py-2.5 text-sm rounded-xl transition-colors hover:bg-emerald-500/10"
                                                style={{ color: 'var(--color-text-secondary)' }}
                                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--color-primary)'}
                                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--color-text-secondary)'}
                                            >
                                                <Settings className="w-4 h-4" />
                                                <span>Settings</span>
                                            </Link>
                                        </div>
                                        <div className="p-2" style={{ borderTop: '1px solid var(--color-input-border)' }}>
                                            <button
                                                onClick={() => {
                                                    setShowProfileMenu(false)
                                                    handleLogout()
                                                }}
                                                className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10 rounded-xl transition-colors"
                                            >
                                                <LogOut className="w-4 h-4" />
                                                <span>Sign Out</span>
                                            </button>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className={`flex-1 min-h-0 ${isChatPage ? 'overflow-hidden' : 'overflow-y-auto overflow-x-hidden'}`}>
                <div className={isChatPage ? 'h-full flex flex-col' : 'max-w-5xl w-full mx-auto px-4 sm:px-6 py-4 sm:py-6 pb-6'}>
                    <Outlet />
                </div>
            </main>

            {/* Mobile Navigation - Hidden on Chat page */}
            {!isChatPage && (
                <nav className="md:hidden shrink-0 backdrop-blur-xl px-2 py-2 safe-area-inset-bottom" style={{ background: 'var(--color-bg-primary)', borderTop: '1px solid var(--color-input-border)' }}>
                    <div className="flex justify-around max-w-md mx-auto">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                end={item.path === '/'}
                                className={({ isActive }) =>
                                    `relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-300 ${isActive
                                        ? ''
                                        : 'active:scale-90'
                                    }`
                                }
                                style={({ isActive }) => ({ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' })}
                            >
                                {({ isActive }) => (
                                    <>
                                        {isActive && (
                                            <div className="absolute inset-0 bg-accent/10 rounded-xl" />
                                        )}
                                        <div className={`relative z-10 ${isActive ? 'scale-110' : ''} transition-transform duration-300`}>
                                            <item.icon className={`w-5 h-5 ${isActive ? 'drop-shadow-[0_0_8px_rgba(0,217,165,0.5)]' : ''}`} style={{ color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)' }} />
                                        </div>
                                        <span className={`relative z-10 text-[10px] font-medium transition-colors ${isActive ? 'text-accent' : ''}`}>
                                            {item.label}
                                        </span>
                                        {isActive && (
                                            <div className="absolute -bottom-0.5 w-4 h-0.5 rounded-full bg-gradient-to-r from-transparent via-accent to-transparent" />
                                        )}
                                    </>
                                )}
                            </NavLink>
                        ))}
                    </div>
                </nav>
            )}

            {showLogoutModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fadeIn"
                        onClick={() => setShowLogoutModal(false)}
                    />

                    {/* Modal */}
                    <div
                        className="relative w-full max-w-sm rounded-2xl shadow-2xl animate-slideUp"
                        style={{
                            background: 'var(--color-bg-elevated)',
                            border: '1px solid var(--color-border)'
                        }}
                    >
                        {/* Close button */}
                        <button
                            onClick={() => setShowLogoutModal(false)}
                            className="absolute top-4 right-4 p-1.5 rounded-lg transition-colors hover:bg-white/10"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            <X className="w-5 h-5" />
                        </button>

                        <div className="p-6 text-center">
                            {/* Icon */}
                            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
                                style={{
                                    background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.1) 100%)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)'
                                }}>
                                <LogOut className="w-8 h-8 text-red-400" />
                            </div>

                            {/* Title */}
                            <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                                Sign Out
                            </h3>

                            {/* Description */}
                            <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
                                Are you sure you want to sign out? You'll need to log in again to access your nutrition data.
                            </p>

                            {/* Buttons */}
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowLogoutModal(false)}
                                    className="flex-1 px-4 py-3 rounded-xl text-sm font-medium transition-all hover:bg-white/5"
                                    style={{
                                        background: 'var(--color-bg-card)',
                                        border: '1px solid var(--color-border)',
                                        color: 'var(--color-text-secondary)'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={confirmLogout}
                                    className="flex-1 px-4 py-3 rounded-xl text-sm font-medium text-white transition-all hover:opacity-90"
                                    style={{
                                        background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                                        boxShadow: '0 4px 15px rgba(239, 68, 68, 0.3)'
                                    }}
                                >
                                    Sign Out
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
