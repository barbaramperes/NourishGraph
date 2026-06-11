import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// In production, API is served from same origin (no prefix needed)
// In development with Vite proxy, /api is proxied to localhost:8000
const API_BASE = import.meta.env.PROD ? '' : '/api'

// Translate raw network errors into user-friendly messages
function friendlyError(err) {
    const msg = err?.message || ''
    if (msg === 'Failed to fetch' || msg.includes('NetworkError') || msg.includes('net::ERR')) {
        return 'Server is temporarily unavailable. Please try again later.'
    }
    return msg
}

async function authFetch(endpoint, options = {}) {
    try {
        const token = localStorage.getItem('nourishgraph-token')
        const headers = {
            'Content-Type': 'application/json',
            ...(token && { Authorization: `Bearer ${token}` })
        }

        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers,
            ...options
        })

        if (!res.ok) {
            const error = await res.json().catch(() => ({}))
            throw new Error(error.detail || `HTTP ${res.status}`)
        }

        return await res.json()
    } catch (err) {
        console.error('Auth API Error:', err)
        // Wrap with friendly message for network errors
        const friendly = friendlyError(err)
        if (friendly !== err.message) {
            const wrapped = new Error(friendly)
            wrapped.original = err
            throw wrapped
        }
        throw err
    }
}

export const useAuthStore = create(
    persist(
        (set, get) => ({
            user: null,
            isAuthenticated: false,
            needsOnboarding: false,
            _hasHydrated: false,
            isLoading: false,
            error: null,

            setHasHydrated: (state) => {
                set({ _hasHydrated: state })
            },

            // Signup with API
            signup: async (email, password, name) => {
                set({ isLoading: true, error: null })
                try {
                    const result = await authFetch('/auth/signup', {
                        method: 'POST',
                        body: JSON.stringify({ email, password, name })
                    })

                    if (result.success && result.token) {
                        // Store token
                        localStorage.setItem('nourishgraph-token', result.token)

                        // Verify token works (prevents redirect loops)
                        const me = await authFetch('/auth/me')
                        const needsOnboarding = !me?.hasProfile

                        set({
                            user: me || result.user,
                            isAuthenticated: true,
                            needsOnboarding,
                            isLoading: false
                        })
                        return { success: true, needsOnboarding }
                    } else {
                        set({ isLoading: false, error: result.message })
                        return { success: false, message: result.message }
                    }
                } catch (err) {
                    localStorage.removeItem('nourishgraph-token')
                    const msg = friendlyError(err)
                    set({ isLoading: false, error: msg })
                    return { success: false, message: msg }
                }
            },

            // Login with API
            login: async (email, password) => {
                set({ isLoading: true, error: null })
                try {
                    const result = await authFetch('/auth/login', {
                        method: 'POST',
                        body: JSON.stringify({ email, password })
                    })

                    if (result.success && result.token) {
                        // Store token
                        localStorage.setItem('nourishgraph-token', result.token)

                        // Verify token works (prevents redirect loops)
                        const me = await authFetch('/auth/me')
                        const needsOnboarding = !me?.hasProfile

                        set({
                            user: me || result.user,
                            isAuthenticated: true,
                            needsOnboarding,
                            isLoading: false
                        })
                        return { success: true, needsOnboarding }
                    } else {
                        set({ isLoading: false, error: result.message })
                        return { success: false, message: result.message }
                    }
                } catch (err) {
                    localStorage.removeItem('nourishgraph-token')
                    const msg = friendlyError(err)
                    set({ isLoading: false, error: msg })
                    return { success: false, message: msg }
                }
            },

            // Google login - now uses backend API
            loginWithGoogle: async (userData) => {
                set({ isLoading: true, error: null })
                try {
                    // Call backend to authenticate Google user
                    const result = await authFetch('/auth/google', {
                        method: 'POST',
                        body: JSON.stringify({
                            email: userData.email,
                            name: userData.name,
                            picture: userData.picture
                        })
                    })

                    if (result.success && result.token) {
                        // Store token
                        localStorage.setItem('nourishgraph-token', result.token)

                        const needsOnboarding = !result.user?.hasProfile

                        set({
                            user: result.user,
                            isAuthenticated: true,
                            needsOnboarding,
                            isLoading: false
                        })
                        return { success: true, needsOnboarding }
                    } else {
                        set({ isLoading: false, error: result.message })
                        return { success: false, message: result.message }
                    }
                } catch (err) {
                    localStorage.removeItem('nourishgraph-token')
                    const msg = friendlyError(err)
                    set({ isLoading: false, error: msg })
                    return { success: false, message: msg }
                }
            },

            completeOnboarding: () => {
                // Mark onboarding as complete (persists for Google users)
                localStorage.setItem('nourishgraph-onboarding-complete', 'true')
                set({ needsOnboarding: false })
            },

            logout: async () => {
                try {
                    await authFetch('/auth/logout', { method: 'POST' })
                } catch (err) {
                    console.error('Logout error:', err)
                }

                localStorage.removeItem('nourishgraph-token')
                set({
                    user: null,
                    isAuthenticated: false,
                    needsOnboarding: false
                })
            },

            // Check if session is still valid
            checkSession: async () => {
                const token = localStorage.getItem('nourishgraph-token')
                if (!token) {
                    set({ isAuthenticated: false, user: null })
                    return false
                }

                try {
                    const user = await authFetch('/auth/me')
                    set({
                        user,
                        isAuthenticated: true,
                        needsOnboarding: !user.hasProfile
                    })
                    return true
                } catch (err) {
                    localStorage.removeItem('nourishgraph-token')
                    set({ isAuthenticated: false, user: null })
                    return false
                }
            },

            updateUser: (updates) => {
                set((state) => ({
                    user: { ...state.user, ...updates }
                }))
            }
        }),
        {
            name: 'nutriai-auth',
            onRehydrateStorage: () => (state) => {
                state?.setHasHydrated(true)
            }
        }
    )
)
