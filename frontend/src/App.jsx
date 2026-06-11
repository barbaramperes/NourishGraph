import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './stores/authStore'
import { useAppStore } from './stores/appStore'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import Privacy from './pages/Privacy'
import ResetPassword from './pages/ResetPassword'
import NotFound from './pages/NotFound'

// Loading spinner component
function LoadingScreen() {
    return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-bg-primary)' }}>
            <div className="text-center">
                <div className="w-12 h-12 border-4 rounded-full animate-spin mx-auto mb-4" style={{ borderColor: 'var(--color-primary)', borderTopColor: 'transparent' }}></div>
                <p style={{ color: 'var(--color-text-muted)' }}>Loading...</p>
            </div>
        </div>
    )
}

function ProtectedRoute({ children }) {
    const { isAuthenticated, _hasHydrated } = useAuthStore()

    // Wait for hydration
    if (!_hasHydrated) {
        return <LoadingScreen />
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return children
}

function AuthRoute({ children }) {
    const { isAuthenticated, needsOnboarding, _hasHydrated } = useAuthStore()

    // Wait for hydration
    if (!_hasHydrated) {
        return <LoadingScreen />
    }

    // Check if onboarding was already completed (persisted flag)
    const onboardingComplete = localStorage.getItem('nourishgraph-onboarding-complete') === 'true'

    if (isAuthenticated && needsOnboarding && !onboardingComplete) {
        return <Navigate to="/onboarding" replace />
    }

    if (isAuthenticated) {
        return <Navigate to="/" replace />
    }

    return children
}

export default function App() {
    const initTheme = useAppStore(state => state.initTheme)
    const loadConversations = useAppStore(state => state.loadConversations)
    const { isAuthenticated, _hasHydrated } = useAuthStore()

    useEffect(() => {
        initTheme()
    }, [initTheme])

    // Load chat history from server when user is authenticated
    useEffect(() => {
        if (_hasHydrated && isAuthenticated) {
            loadConversations()
        }
    }, [_hasHydrated, isAuthenticated, loadConversations])

    return (
        <ErrorBoundary>
            <BrowserRouter>
                <Routes>
                    {/* Public Routes */}
                    <Route path="/privacy" element={<Privacy />} />

                    {/* Auth Routes */}
                    <Route path="/login" element={
                        <AuthRoute><Login /></AuthRoute>
                    } />
                    <Route path="/signup" element={
                        <AuthRoute><Signup /></AuthRoute>
                    } />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    
                    {/* Default route for non-authenticated users goes to login */}
                    <Route path="/auth" element={<Navigate to="/login" replace />} />
                    <Route path="/onboarding" element={
                        <ProtectedRoute><Onboarding /></ProtectedRoute>
                    } />

                    {/* Protected Routes */}
                    <Route path="/" element={
                        <ProtectedRoute><Layout /></ProtectedRoute>
                    }>
                        <Route index element={<Dashboard />} />
                        <Route path="chat" element={<Chat />} />
                        <Route path="profile" element={<Profile />} />
                        <Route path="settings" element={<Settings />} />
                    </Route>

                    {/* 404 Catch-all */}
                    <Route path="*" element={<NotFound />} />
                </Routes>
            </BrowserRouter>
        </ErrorBoundary>
    )
}
