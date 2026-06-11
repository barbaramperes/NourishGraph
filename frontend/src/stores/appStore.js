import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// In production, API is served from same origin (no prefix needed)
// In development with Vite proxy, /api is proxied to localhost:8000
const API_BASE = import.meta.env.PROD ? '' : '/api'

// Error types for better handling
const ErrorType = {
    NETWORK: 'network',
    AUTH: 'auth',
    SERVER: 'server',
    TIMEOUT: 'timeout',
    ABORTED: 'aborted'
}

async function apiFetch(endpoint, options = {}) {
    try {
        const token = localStorage.getItem('nourishgraph-token')

        // If no token, return auth error
        if (!token) {
            return { error: true, type: ErrorType.AUTH, message: 'Not authenticated' }
        }

        const headers = {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
            ...options.headers
        }

        // Support for AbortController
        const fetchOptions = {
            ...options,
            headers
        }
        if (options.signal) {
            fetchOptions.signal = options.signal
        }

        const res = await fetch(`${API_BASE}${endpoint}`, fetchOptions)

        if (!res.ok) {
            // 401 means token is invalid
            if (res.status === 401) {
                console.warn('API: Not authenticated')
                return { error: true, type: ErrorType.AUTH, message: 'Session expired. Please log in again.' }
            }

            // 503 means service unavailable
            if (res.status === 503) {
                return { error: true, type: ErrorType.SERVER, message: 'Service temporarily unavailable. Please try again.' }
            }

            // 500 means server error
            if (res.status >= 500) {
                const payload = await res.json().catch(() => null)
                return { error: true, type: ErrorType.SERVER, message: payload?.detail || 'Server error. Please try again.' }
            }

            const payload = await res.json().catch(() => null)
            const detail = payload?.detail || payload?.message || `Error ${res.status}`
            console.error('API Error:', detail)
            return { error: true, type: ErrorType.SERVER, message: detail }
        }

        return await res.json()
    } catch (err) {
        // Abort errors
        if (err.name === 'AbortError') {
            return { aborted: true, type: ErrorType.ABORTED }
        }

        // Network errors (no connection)
        if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
            console.error('Network Error:', err)
            return { error: true, type: ErrorType.NETWORK, message: 'Unable to connect to server. Please check your connection.' }
        }

        console.error('API Error:', err)
        return { error: true, type: ErrorType.SERVER, message: 'Something went wrong. Please try again.' }
    }
}

// Calculate BMR using Mifflin-St Jeor
function calculateBMR(weight, height, age, gender) {
    if (!weight || !height || !age) return null
    const base = 10 * weight + 6.25 * height - 5 * age
    // Check for male (M, male, Male, etc.)
    const isMale = gender && (gender.toUpperCase() === 'M' || gender.toLowerCase().startsWith('m'))
    return Math.round(isMale ? base + 5 : base - 161)
}

// Calculate TDEE based on activity level
function calculateTDEE(bmr, activity) {
    if (!bmr) return null
    const multipliers = {
        sedentary: 1.2,
        light: 1.375,
        moderate: 1.55,
        active: 1.725,
        very_active: 1.9
    }
    return Math.round(bmr * (multipliers[activity] || 1.55))
}

// Calculate calorie goal based on objective
function calculateCalorieGoal(tdee, goal) {
    if (!tdee) return null
    // Handle both frontend and backend goal names
    if (goal === 'lose_weight' || goal === 'lose') return Math.round(tdee - 500)
    if (goal === 'gain_muscle' || goal === 'gain') return Math.round(tdee + 300)
    return tdee // maintain
}

// Generate smart chat title based on message content
function generateChatTitle(msg) {
    const lower = msg.toLowerCase()
    // Detect common topics and create meaningful titles
    if (lower.includes('intermittent fasting') || lower.includes('fasting')) return 'Intermittent Fasting'
    if (lower.includes('vitamin d')) return 'Vitamin D Benefits'
    if (lower.includes('vitamin b12') || lower.includes('b12')) return 'Vitamin B12'
    if (lower.includes('vitamin')) return 'Vitamins & Supplements'
    if (lower.includes('protein')) return 'Protein Intake'
    if (lower.includes('calorie') || lower.includes('calories')) return 'Calorie Needs'
    if (lower.includes('weight loss') || lower.includes('lose weight')) return 'Weight Loss'
    if (lower.includes('weight goal') || lower.includes('reach my goal')) return 'Weight Goals'
    if (lower.includes('weight')) return 'Weight Management'
    if (lower.includes('muscle') || lower.includes('gain')) return 'Muscle Building'
    if (lower.includes('diet') || lower.includes('meal plan')) return 'Meal Planning'
    if (lower.includes('iron') || lower.includes('anemia')) return 'Iron & Anemia'
    if (lower.includes('omega') || lower.includes('fish oil')) return 'Omega Fatty Acids'
    if (lower.includes('microbiome') || lower.includes('gut')) return 'Gut Health'
    if (lower.includes('diabetes') || lower.includes('blood sugar') || lower.includes('glucose')) return 'Blood Sugar'
    if (lower.includes('immune')) return 'Immune System'
    if (lower.includes('eat') || lower.includes('food')) return 'Nutrition Advice'
    if (lower.includes('research') || lower.includes('study')) return 'Research Query'
    if (lower.includes('recipe') || lower.includes('cook')) return 'Recipe Ideas'
    if (lower.includes('breakfast') || lower.includes('lunch') || lower.includes('dinner')) return 'Meal Ideas'
    // Default: use first meaningful words
    const words = msg.split(' ').slice(0, 5).join(' ')
    return words.length > 30 ? words.slice(0, 30) + '...' : words
}

export const useAppStore = create(
    persist(
        (set, get) => ({
            // Theme
            theme: 'light',  // Default to light

            setTheme: (theme) => {
                document.documentElement.setAttribute('data-theme', theme)
                set({ theme })
            },

            toggleTheme: () => {
                const newTheme = get().theme === 'dark' ? 'light' : 'dark'
                document.documentElement.setAttribute('data-theme', newTheme)
                set({ theme: newTheme })
            },

            initTheme: () => {
                // Sync theme from DOM if different, or apply stored theme
                const currentDOMTheme = document.documentElement.getAttribute('data-theme')
                const storedTheme = get().theme

                if (currentDOMTheme && currentDOMTheme !== storedTheme) {
                    // DOM has a different theme, update store to match
                    set({ theme: currentDOMTheme })
                } else {
                    // Apply stored theme to DOM
                    document.documentElement.setAttribute('data-theme', storedTheme)
                }
            },

            // Profile - persisted locally
            profile: {
                name: '',
                email: '',
                age: null,
                gender: '',
                weight: null,
                height: null,
                goal: '',
                activity: 'moderate',
                diet: null,
                allergies: [],
                calorie_goal: 2000,
                protein_goal: 150,
                carbs_goal: 250,
                fat_goal: 65
            },

            // Meals
            meals: [],
            dailyTotals: { calories: 0, protein: 0, carbs: 0, fat: 0 },

            // Chat
            messages: [],
            sources: [],
            isTyping: false,
            abortController: null,

            // Chat History
            chatHistory: [],
            currentChatId: null,

            // Favorite Messages
            favoriteMessages: [],

            // Proactive Agent Interventions
            interventions: [],
            interventionsLoading: false,
            lastInterventionCheck: null,

            // Goals
            goals: [],
            goalsLoading: false,

            // Loading states
            profileLoading: false,

            // Actions
            loadProfile: async () => {
                // Prevent duplicate calls
                if (get().profileLoading) {
                    return get().profile
                }

                set({ profileLoading: true })

                try {
                    // First try to load from server
                    const serverProfile = await apiFetch('/profile')

                    // Handle errors gracefully
                    if (serverProfile?.error) {
                        console.warn('Could not load profile:', serverProfile.message)
                        return get().profile // Return local profile as fallback
                    }

                    if (serverProfile && serverProfile.name) {
                        // Map sex to gender for compatibility
                        const mappedProfile = {
                            ...serverProfile,
                            gender: serverProfile.sex || serverProfile.gender
                        }
                        // Smart merge: don't overwrite local non-null values with server nulls
                        // This prevents a race where loadProfile overwrites a just-saved diet
                        const currentProfile = get().profile
                        const merged = { ...currentProfile }
                        for (const [key, value] of Object.entries(mappedProfile)) {
                            // Only overwrite if server has a real value OR local doesn't have one
                            if (value !== null && value !== undefined) {
                                merged[key] = value
                            } else if (currentProfile[key] === null || currentProfile[key] === undefined || currentProfile[key] === '') {
                                merged[key] = value
                            }
                            // Otherwise keep local value (server returned null but local has data)
                        }
                        set({ profile: merged })
                        return merged
                    }
                    // If not on server, return local profile
                    return get().profile
                } finally {
                    set({ profileLoading: false })
                }
            },

            saveProfile: async (data) => {
                // Calculate calorie goals locally first
                const bmr = calculateBMR(data.weight, data.height, data.age, data.gender)
                const tdee = calculateTDEE(bmr, data.activity)
                const calorie_goal = calculateCalorieGoal(tdee, data.goal)

                // Calculate macros based on calories
                const weight = parseFloat(data.weight) || 70
                const protein_goal = calorie_goal ? Math.round(weight * 2) : null
                const fat_goal = calorie_goal ? Math.round((calorie_goal * 0.25) / 9) : null
                const carbs_goal = calorie_goal ? Math.round((calorie_goal - (protein_goal * 4) - (fat_goal * 9)) / 4) : null

                const profileWithGoals = {
                    ...data,
                    bmr,
                    tdee,
                    calorie_goal,
                    protein_goal,
                    carbs_goal,
                    fat_goal
                }

                // Try to send to server first
                const token = localStorage.getItem('nourishgraph-token')
                if (token) {
                    const result = await apiFetch('/profile', {
                        method: 'POST',
                        body: JSON.stringify(profileWithGoals)
                    })

                    // Handle errors
                    if (result?.error) {
                        console.warn('Could not save profile to server:', result.message)
                        // Fall through to local save
                    } else if (result && result.profile) {
                        // Use server-calculated values (more accurate)
                        const serverProfile = {
                            ...result.profile,
                            gender: result.profile.sex || result.profile.gender
                        }
                        set({ profile: serverProfile })
                        return serverProfile
                    }
                }

                // Fallback to local save
                set({ profile: profileWithGoals })
                return profileWithGoals
            },

            updateProfile: (updates) => {
                set((state) => ({
                    profile: { ...state.profile, ...updates }
                }))
            },

            loadMeals: async () => {
                const data = await apiFetch('/meals')

                // Handle errors gracefully
                if (data?.error) {
                    console.warn('Could not load meals:', data.message)
                    return null
                }

                if (data) {
                    set({
                        meals: data.meals || [],
                        dailyTotals: data.totals || { calories: 0, protein: 0, carbs: 0, fat: 0 }
                    })
                }
                return data
            },

            addMeal: async (meal) => {
                const result = await apiFetch('/meals', {
                    method: 'POST',
                    body: JSON.stringify(meal)
                })
                if (result) {
                    await get().loadMeals()
                }
                return result
            },

            searchFoods: async (query) => {
                if (!query || query.length < 2) return []
                return await apiFetch(`/foods/search?q=${encodeURIComponent(query)}&limit=10`) || []
            },

            sendMessage: async (message) => {
                const state = get()
                const profile = state.profile // Get current profile to send with message

                // Create AbortController for this request
                const abortController = new AbortController()
                set({ abortController })

                // If user sends CONFIRM or CANCEL, clear requiresConfirmation from previous messages
                const msgLower = message.trim().toLowerCase()
                if (msgLower === 'confirm' || msgLower === 'cancel' || msgLower === 'confirmar' || msgLower === 'cancelar') {
                    set((state) => ({
                        messages: state.messages.map(msg =>
                            msg.requiresConfirmation
                                ? { ...msg, requiresConfirmation: false }
                                : msg
                        )
                    }))
                }

                // Create a new chat if none exists
                if (!state.currentChatId) {
                    const newChat = {
                        id: crypto.randomUUID(),
                        name: generateChatTitle(message),
                        createdAt: new Date().toISOString(),
                        updatedAt: new Date().toISOString(),
                        messages: []
                    }
                    set({
                        chatHistory: [newChat, ...state.chatHistory],
                        currentChatId: newChat.id
                    })
                }

                set((state) => ({
                    messages: [...state.messages, { role: 'user', content: message }],
                    isTyping: true
                }))

                // Update chat title if it's still "New Conversation" and this is the first message
                const currentState = get()
                const currentChat = currentState.chatHistory.find(c => c.id === currentState.currentChatId)
                if (currentChat && (currentChat.name === 'New Conversation' || currentChat.name === 'New Chat')) {
                    set((s) => ({
                        chatHistory: s.chatHistory.map(chat =>
                            chat.id === currentState.currentChatId
                                ? { ...chat, name: generateChatTitle(message) }
                                : chat
                        )
                    }))
                }

                const res = await apiFetch('/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        message,
                        profile: profile, // Send current profile with each message
                        chat_id: get().currentChatId // Send conversation ID for server persistence
                    }),
                    signal: abortController.signal
                })

                // If aborted, don't update messages
                if (res?.aborted) {
                    set({ isTyping: false, abortController: null })
                    return null
                }

                // Handle errors with specific messages
                let errorMessage = null
                if (res?.error) {
                    switch (res.type) {
                        case 'network':
                            errorMessage = '🔌 **Connection Error**\n\nUnable to reach the server. Please check your internet connection and try again.'
                            break
                        case 'auth':
                            errorMessage = '🔐 **Session Expired**\n\nPlease log in again to continue.'
                            break
                        case 'server':
                            errorMessage = `⚠️ **Server Error**\n\n${res.message || 'Something went wrong. Please try again in a moment.'}`
                            break
                        default:
                            errorMessage = `❌ **Error**\n\n${res.message || 'An unexpected error occurred.'}`
                    }
                }

                const assistantMessage = {
                    role: 'assistant',
                    content: errorMessage || res?.response || '❌ Unable to get response. Please try again.',
                    sources: res?.sources || [],
                    requiresConfirmation: !!res?.requires_confirmation,
                    pending: res?.pending || null,
                    agent: res?.agent || null,
                    intent: res?.intent || null,
                    toolsUsed: res?.tools_used || [],
                    isError: !!errorMessage,
                    evidenceLevel: res?.evidence_level || null,
                    calculations: res?.calculations || null,
                    // Safety fields - show softer SafetyMessage when supplement+medication combined
                    safetyType: res?.safety_flags?.some(f => f.includes('emergency') || f.includes('self_harm') || f.includes('crisis')) ? 'emergency'
                        : res?.safety_flags?.some(f => f.includes('eating_disorder')) ? 'eating_disorder'
                        : res?.safety_flags?.some(f => f.includes('supplement_for_symptom')) ? 'medication'
                        : (res?.safety_flags?.some(f => f.includes('supplement')) && res?.safety_flags?.some(f => f.includes('medication'))) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('supplement')) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('medication')) ? 'medication'
                        : null,
                    safetyMessage: (res?.safety_level === 'warning' || res?.safety_level === 'caution')
                        ? 'This topic requires careful consideration. Please consult a healthcare professional.'
                        : null,
                }

                set((state) => {
                    const updatedMessages = [...state.messages, assistantMessage]

                    // Update chat history with new messages
                    const updatedHistory = state.chatHistory.map(chat =>
                        chat.id === state.currentChatId
                            ? { ...chat, messages: updatedMessages, updatedAt: new Date().toISOString() }
                            : chat
                    )

                    return {
                        messages: updatedMessages,
                        sources: res?.sources || state.sources,
                        isTyping: false,
                        abortController: null,
                        chatHistory: updatedHistory
                    }
                })

                // If profile was updated on server, reload it to sync frontend state
                if (res?.profile_updated) {
                    // Small delay to ensure DB transaction is committed
                    setTimeout(async () => {
                        await get().loadProfile()
                    }, 500)
                }

                return res
            },

            /**
             * Send message with streaming response (SSE)
             * Shows response progressively as it's generated
             */
            sendMessageStreaming: async (message, callbacks = {}) => {
                const state = get()
                const profile = state.profile
                const token = localStorage.getItem('nourishgraph-token')

                const { onChunk, onIntent, onTool, onAgent, onDone, onError } = callbacks

                // If user sends CONFIRM or CANCEL, clear requiresConfirmation from previous messages
                const msgLower = message.trim().toLowerCase()
                if (msgLower === 'confirm' || msgLower === 'cancel' || msgLower === 'confirmar' || msgLower === 'cancelar') {
                    set((state) => ({
                        messages: state.messages.map(msg =>
                            msg.requiresConfirmation
                                ? { ...msg, requiresConfirmation: false }
                                : msg
                        )
                    }))
                }

                // Create AbortController for this request
                const abortController = new AbortController()
                set({ abortController })

                // Create a new chat if none exists
                if (!state.currentChatId) {
                    const newChat = {
                        id: crypto.randomUUID(),
                        name: generateChatTitle(message),
                        createdAt: new Date().toISOString(),
                        updatedAt: new Date().toISOString(),
                        messages: []
                    }
                    set({
                        chatHistory: [newChat, ...state.chatHistory],
                        currentChatId: newChat.id
                    })
                }

                // Update chat title if it's still "New Conversation" and this is the first real message
                const currentState = get()
                const currentChat = currentState.chatHistory.find(c => c.id === currentState.currentChatId)
                if (currentChat && (currentChat.name === 'New Conversation' || currentChat.name === 'New Chat')) {
                    const newTitle = generateChatTitle(message)
                    set((s) => ({
                        chatHistory: s.chatHistory.map(chat =>
                            chat.id === currentState.currentChatId
                                ? { ...chat, name: newTitle }
                                : chat
                        )
                    }))
                }

                // Add user message
                const userMessage = { role: 'user', content: message }
                set((s) => ({
                    messages: [...s.messages, userMessage],
                    isTyping: true
                }))

                // IMMEDIATELY save user message to chat history (don't wait for response)
                set((s) => ({
                    chatHistory: s.chatHistory.map(chat =>
                        chat.id === s.currentChatId
                            ? { ...chat, messages: [...s.messages], updatedAt: new Date().toISOString() }
                            : chat
                    )
                }))

                // Add placeholder for streaming assistant message
                const assistantMsgIndex = get().messages.length
                set((s) => ({
                    messages: [...s.messages, { role: 'assistant', content: '', isStreaming: true }]
                }))

                try {
                    const response = await fetch(`${API_BASE}/chat/stream`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`,
                        },
                        body: JSON.stringify({ message, profile, chat_id: get().currentChatId }),
                        signal: abortController.signal,
                    })

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`)
                    }

                    const reader = response.body.getReader()
                    const decoder = new TextDecoder()
                    let buffer = ''
                    let fullText = ''
                    let intent = 'chat'
                    let toolsUsed = []
                    let sources = []
                    let calculations = null
                    let agentInfo = null
                    let confidence = null
                    let safetyLevel = null
                    let safetyFlags = null
                    let requiresConfirmation = false
                    let pending = null

                    while (true) {
                        const { done, value } = await reader.read()
                        if (done) break

                        buffer += decoder.decode(value, { stream: true })
                        const lines = buffer.split('\n')
                        buffer = lines.pop() || ''

                        let eventType = null
                        for (const line of lines) {
                            if (line.startsWith('event: ')) {
                                eventType = line.slice(7).trim()
                            } else if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6))

                                    switch (eventType) {
                                        case 'intent':
                                            intent = data.intent
                                            onIntent?.(intent)
                                            break

                                        case 'agent':
                                            agentInfo = data.agent
                                            confidence = data.confidence
                                            toolsUsed = data.tools_used || []
                                            onAgent?.({ agent: agentInfo, confidence, toolsUsed })
                                            break

                                        case 'tool':
                                            toolsUsed.push(data.tool)
                                            onTool?.(data.tool)
                                            break

                                        case 'chunk':
                                            fullText += data.text
                                            // Don't update UI on each chunk - wait for done event
                                            // This prevents the "letter by letter" typing effect
                                            onChunk?.(data.text, fullText)
                                            break

                                        case 'sources':
                                            sources = data.sources || []
                                            break

                                        case 'done':
                                            fullText = data.response
                                            intent = data.intent
                                            toolsUsed = data.tools_used || []
                                            sources = data.sources || sources
                                            calculations = data.calculations || null
                                            agentInfo = data.agent || agentInfo
                                            confidence = data.confidence ?? confidence
                                            safetyLevel = data.safety_level || null
                                            safetyFlags = data.safety_flags || null
                                            requiresConfirmation = !!data.requires_confirmation
                                            pending = data.pending || null
                                            break

                                        case 'error':
                                            throw new Error(data.message)
                                    }
                                } catch (e) {
                                    console.warn('SSE parse error:', e)
                                }
                            }
                        }
                    }

                    // Finalize the assistant message
                    const finalMessage = {
                        role: 'assistant',
                        content: fullText,
                        sources,
                        intent,
                        toolsUsed,
                        isStreaming: false,
                        evidenceLevel: null,
                        calculations,
                        agentInfo,
                        confidence,
                        requiresConfirmation,
                        pending,
                        safetyType: safetyFlags?.some(f => f.includes('emergency') || f.includes('self_harm') || f.includes('crisis')) ? 'emergency'
                            : safetyFlags?.some(f => f.includes('eating_disorder')) ? 'eating_disorder'
                            : safetyFlags?.some(f => f.includes('supplement_for_symptom')) ? 'medication'
                            : (safetyFlags?.some(f => f.includes('supplement')) && safetyFlags?.some(f => f.includes('medication'))) ? 'supplement'
                            : safetyFlags?.some(f => f.includes('supplement')) ? 'supplement'
                            : safetyFlags?.some(f => f.includes('medication')) ? 'medication'
                            : null,
                        safetyMessage: (safetyLevel === 'warning' || safetyLevel === 'caution')
                            ? 'This topic requires careful consideration. Please consult a healthcare professional.'
                            : null,
                    }

                    set((s) => {
                        const updatedMessages = s.messages.map((m, i) =>
                            i === assistantMsgIndex ? finalMessage : m
                        )

                        const updatedHistory = s.chatHistory.map(chat =>
                            chat.id === s.currentChatId
                                ? { ...chat, messages: updatedMessages, updatedAt: new Date().toISOString() }
                                : chat
                        )

                        return {
                            messages: updatedMessages,
                            sources,
                            isTyping: false,
                            abortController: null,
                            chatHistory: updatedHistory
                        }
                    })

                    onDone?.({ response: fullText, intent, toolsUsed, sources })
                    return { response: fullText, intent, tools_used: toolsUsed, sources }

                } catch (err) {
                    if (err.name === 'AbortError') {
                        set({ isTyping: false, abortController: null })
                        return { aborted: true }
                    }

                    console.error('Streaming error:', err)
                    onError?.(err)

                    // Update message with error
                    set((s) => ({
                        messages: s.messages.map((m, i) =>
                            i === assistantMsgIndex
                                ? { ...m, content: '❌ Error: ' + err.message, isStreaming: false }
                                : m
                        ),
                        isTyping: false,
                        abortController: null
                    }))

                    return null
                }
            },

            // Stop generating response
            stopGeneration: () => {
                const { abortController } = get()
                if (abortController) {
                    abortController.abort()
                    set({ isTyping: false, abortController: null })
                }
            },

            regenerateMessage: async (messageIndex) => {
                const state = get()
                const profile = state.profile

                // First, abort any ongoing request
                const { abortController: existingController } = get()
                if (existingController) {
                    existingController.abort()
                }

                // Create new AbortController
                const abortController = new AbortController()

                // Find the last user message before this assistant message
                let userMessageIndex = messageIndex - 1
                while (userMessageIndex >= 0 && state.messages[userMessageIndex]?.role !== 'user') {
                    userMessageIndex--
                }

                if (userMessageIndex < 0) return null

                const userMessage = state.messages[userMessageIndex].content

                // Remove the assistant message we're regenerating
                const messagesBeforeRegenerate = state.messages.slice(0, messageIndex)

                set({
                    messages: messagesBeforeRegenerate,
                    isTyping: true,
                    abortController
                })

                const res = await apiFetch('/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        message: userMessage,
                        profile: profile
                    }),
                    signal: abortController.signal
                })

                // If aborted, don't update
                if (res?.aborted) {
                    return null
                }

                const assistantMessage = {
                    role: 'assistant',
                    content: res?.response || '❌ Connection error. Please check if the server is running.',
                    sources: res?.sources || [],
                    requiresConfirmation: !!res?.requires_confirmation,
                    pending: res?.pending || null,
                    agent: res?.agent || null,
                    intent: res?.intent || null,
                    toolsUsed: res?.tools_used || [],
                    evidenceLevel: res?.evidence_level || null,
                    calculations: res?.calculations || null,
                    safetyType: res?.safety_flags?.some(f => f.includes('emergency') || f.includes('self_harm') || f.includes('crisis')) ? 'emergency'
                        : res?.safety_flags?.some(f => f.includes('eating_disorder')) ? 'eating_disorder'
                        : res?.safety_flags?.some(f => f.includes('supplement_for_symptom')) ? 'medication'
                        : (res?.safety_flags?.some(f => f.includes('supplement')) && res?.safety_flags?.some(f => f.includes('medication'))) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('supplement')) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('medication')) ? 'medication'
                        : null,
                    safetyMessage: (res?.safety_level === 'warning' || res?.safety_level === 'caution')
                        ? 'This topic requires careful consideration. Please consult a healthcare professional.'
                        : null,
                }

                set((state) => {
                    const updatedMessages = [...messagesBeforeRegenerate, assistantMessage]

                    const updatedHistory = state.chatHistory.map(chat =>
                        chat.id === state.currentChatId
                            ? { ...chat, messages: updatedMessages, updatedAt: new Date().toISOString() }
                            : chat
                    )

                    return {
                        messages: updatedMessages,
                        sources: res?.sources || state.sources,
                        isTyping: false,
                        abortController: null,
                        chatHistory: updatedHistory
                    }
                })

                return res
            },

            editAndResendMessage: async (messageIndex, newContent) => {
                const state = get()
                const profile = state.profile

                // First, abort any ongoing request
                const { abortController: existingController } = get()
                if (existingController) {
                    existingController.abort()
                }

                // Create new AbortController for this request
                const abortController = new AbortController()

                // Remove all messages from this point onwards
                const messagesBeforeEdit = state.messages.slice(0, messageIndex)

                set({
                    messages: [...messagesBeforeEdit, { role: 'user', content: newContent }],
                    isTyping: true,
                    abortController
                })

                const res = await apiFetch('/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        message: newContent,
                        profile: profile
                    }),
                    signal: abortController.signal
                })

                // If aborted, don't update
                if (res?.aborted) {
                    return null
                }

                const assistantMessage = {
                    role: 'assistant',
                    content: res?.response || '❌ Connection error. Please check if the server is running.',
                    sources: res?.sources || [],
                    requiresConfirmation: !!res?.requires_confirmation,
                    pending: res?.pending || null,
                    agent: res?.agent || null,
                    intent: res?.intent || null,
                    toolsUsed: res?.tools_used || [],
                    evidenceLevel: res?.evidence_level || null,
                    calculations: res?.calculations || null,
                    safetyType: res?.safety_flags?.some(f => f.includes('emergency') || f.includes('self_harm') || f.includes('crisis')) ? 'emergency'
                        : res?.safety_flags?.some(f => f.includes('eating_disorder')) ? 'eating_disorder'
                        : res?.safety_flags?.some(f => f.includes('supplement_for_symptom')) ? 'medication'
                        : (res?.safety_flags?.some(f => f.includes('supplement')) && res?.safety_flags?.some(f => f.includes('medication'))) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('supplement')) ? 'supplement'
                        : res?.safety_flags?.some(f => f.includes('medication')) ? 'medication'
                        : null,
                    safetyMessage: (res?.safety_level === 'warning' || res?.safety_level === 'caution')
                        ? 'This topic requires careful consideration. Please consult a healthcare professional.'
                        : null,
                }

                set((state) => {
                    const updatedMessages = [...messagesBeforeEdit, { role: 'user', content: newContent }, assistantMessage]

                    const updatedHistory = state.chatHistory.map(chat =>
                        chat.id === state.currentChatId
                            ? { ...chat, messages: updatedMessages, updatedAt: new Date().toISOString() }
                            : chat
                    )

                    return {
                        messages: updatedMessages,
                        sources: res?.sources || state.sources,
                        isTyping: false,
                        abortController: null,
                        chatHistory: updatedHistory
                    }
                })

                return res
            },

            clearChat: async () => {
                // Clear ALL chats - start fresh with a new conversation
                const state = get()
                
                // Create a new chat to start fresh (instant UI feedback)
                const newChat = {
                    id: crypto.randomUUID(),
                    name: 'New Conversation',
                    messages: [],
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                }
                
                set({
                    messages: [],
                    sources: [],
                    isTyping: false,
                    chatHistory: [newChat],
                    currentChatId: newChat.id
                })
                
                // Delete all conversations from server (await all)
                try {
                    await Promise.all(
                        state.chatHistory.map(chat =>
                            apiFetch(`/conversations/${chat.id}`, { method: 'DELETE' })
                        )
                    )
                } catch (err) {
                    console.error('Error deleting conversations from server:', err)
                }
            },

            createNewChat: () => {
                const state = get()

                // Cancel any ongoing request when creating new chat
                if (state.abortController) {
                    state.abortController.abort()
                }

                const newChat = {
                    id: crypto.randomUUID(),
                    name: 'New Conversation',
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                    messages: []
                }
                set((state) => ({
                    chatHistory: [newChat, ...state.chatHistory],
                    currentChatId: newChat.id,
                    messages: [],
                    sources: [],
                    isTyping: false,  // Reset typing state
                    abortController: null  // Clear abort controller
                }))
            },

            switchChat: (chatId) => {
                const state = get()

                // Cancel any ongoing request when switching chats
                if (state.abortController) {
                    state.abortController.abort()
                }

                const chat = state.chatHistory.find(c => c.id === chatId)
                if (chat) {
                    set({
                        currentChatId: chatId,
                        messages: chat.messages || [],
                        sources: [],
                        isTyping: false,  // Reset typing state
                        abortController: null  // Clear abort controller
                    })
                }
            },

            deleteChat: async (chatId) => {
                // Snapshot current state in case we need to rollback
                const prev = get()
                const deletedChat = prev.chatHistory.find(c => c.id === chatId)

                // Optimistic: remove locally immediately for responsive UI
                set((state) => {
                    const newHistory = state.chatHistory.filter(c => c.id !== chatId)
                    const isCurrentChat = state.currentChatId === chatId
                    return {
                        chatHistory: newHistory,
                        currentChatId: isCurrentChat ? (newHistory[0]?.id || null) : state.currentChatId,
                        messages: isCurrentChat ? (newHistory[0]?.messages || []) : state.messages,
                        sources: isCurrentChat ? [] : state.sources
                    }
                })

                // Actually delete from server — await to ensure DB deletion
                try {
                    const res = await apiFetch(`/conversations/${chatId}`, { method: 'DELETE' })
                    if (res?.error) {
                        console.error('Server refused delete:', res.message)
                        // Rollback: restore conversation locally
                        if (deletedChat) {
                            set((state) => ({
                                chatHistory: [deletedChat, ...state.chatHistory]
                            }))
                        }
                    }
                } catch (err) {
                    console.error('Error deleting conversation from server:', err)
                    // Rollback: restore conversation locally
                    if (deletedChat) {
                        set((state) => ({
                            chatHistory: [deletedChat, ...state.chatHistory]
                        }))
                    }
                }
            },

            renameChat: (chatId, newName) => {
                set((state) => ({
                    chatHistory: state.chatHistory.map(chat =>
                        chat.id === chatId ? { ...chat, name: newName } : chat
                    )
                }))
            },

            // Toggle favorite on a message
            toggleFavorite: (chatId, messageIndex) => {
                set((state) => {
                    const existingIndex = state.favoriteMessages.findIndex(
                        f => f.chatId === chatId && f.messageIndex === messageIndex
                    )
                    if (existingIndex >= 0) {
                        // Remove from favorites
                        return {
                            favoriteMessages: state.favoriteMessages.filter((_, i) => i !== existingIndex)
                        }
                    } else {
                        // Add to favorites with timestamp
                        const chat = state.chatHistory.find(c => c.id === chatId)
                        const message = chat?.messages?.[messageIndex] || state.messages[messageIndex]
                        return {
                            favoriteMessages: [
                                ...state.favoriteMessages,
                                {
                                    chatId,
                                    messageIndex,
                                    content: message?.content || '',
                                    timestamp: new Date().toISOString()
                                }
                            ]
                        }
                    }
                })
            },

            clearAllData: () => {
                // Clear localStorage
                localStorage.removeItem('nutriai-app')
                // Reset state
                set({
                    messages: [],
                    chatHistory: [],
                    currentChatId: null,
                    sources: [],
                    favoriteMessages: [],
                    meals: [],
                    dailyTotals: { calories: 0, protein: 0, carbs: 0, fat: 0 },
                })
            },

            /**
             * Load conversations from the server.
             * Called on login/app init to sync chat history across browser windows.
             */
            loadConversations: async () => {
                try {
                    const res = await apiFetch('/conversations')
                    if (res?.error || !res?.conversations) return

                    const serverConversations = res.conversations

                    // Server is source of truth for persisted conversations.
                    // Only keep local conversations that have NO messages yet
                    // (brand-new chats the user just created but hasn't sent a message).
                    const localHistory = get().chatHistory
                    const serverIds = new Set(serverConversations.map(c => c.id))

                    // Keep local-only chats that are empty placeholders (not yet on server)
                    const localOnlyEmpty = localHistory.filter(c => 
                        !serverIds.has(c.id) && (!c.messages || c.messages.length === 0)
                    )

                    // Combined: empty local placeholders + everything from server
                    const merged = [...localOnlyEmpty, ...serverConversations]

                    // Sort by updatedAt descending
                    merged.sort((a, b) => {
                        const dateA = new Date(a.updatedAt || a.createdAt || 0)
                        const dateB = new Date(b.updatedAt || b.createdAt || 0)
                        return dateB - dateA
                    })

                    const currentChatId = get().currentChatId
                    const currentChat = merged.find(c => c.id === currentChatId)

                    set({
                        chatHistory: merged,
                        // If current chat came from server, load its messages
                        ...(currentChat ? {
                            messages: currentChat.messages || []
                        } : {})
                    })

                    console.log(`📜 Loaded ${serverConversations.length} conversations from server, ${localOnlyEmpty.length} local-only empty`)
                } catch (err) {
                    console.error('Error loading conversations:', err)
                }
            },

            // ============================================
            // AGENT INTEGRATION FUNCTIONS
            // ============================================

            // Get food suggestions for a specific nutritional goal
            suggestFoodsForGoal: async (goal, nutrient = null) => {
                const { profile } = get()

                set({ isTyping: true })

                try {
                    let prompt = `Suggest foods for ${goal}`

                    if (nutrient) {
                        prompt += ` rich in ${nutrient}`
                    }

                    if (profile.goal) {
                        const goalMap = {
                            'lose_weight': 'weight loss',
                            'maintain': 'weight maintenance',
                            'gain_muscle': 'muscle gain'
                        }
                        prompt += ` suitable for ${goalMap[profile.goal] || profile.goal}`
                    }

                    const response = await apiFetch('/chat', {
                        method: 'POST',
                        body: JSON.stringify({
                            message: prompt,
                            profile: profile
                        })
                    })

                    set({ isTyping: false })

                    return {
                        success: true,
                        suggestions: response.response || response.message,
                        sources: response.sources || []
                    }
                } catch (error) {
                    console.error('Error getting food suggestions:', error)
                    set({ isTyping: false })
                    return {
                        success: false,
                        error: error.message || 'Error getting food suggestions'
                    }
                }
            },

            // Analyze nutritional content of a meal or food
            analyzeNutrition: async (foodOrMeal) => {
                const { profile } = get()

                set({ isTyping: true })

                try {
                    const prompt = `Analyze the nutritional information of: ${foodOrMeal}. Include calories, protein, carbs, fats, vitamins and important minerals.`

                    const response = await apiFetch('/chat', {
                        method: 'POST',
                        body: JSON.stringify({
                            message: prompt,
                            profile: profile
                        })
                    })

                    set({ isTyping: false })

                    return {
                        success: true,
                        analysis: response.response || response.message,
                        sources: response.sources || []
                    }
                } catch (error) {
                    console.error('Error analyzing nutrition:', error)
                    set({ isTyping: false })
                    return {
                        success: false,
                        error: error.message || 'Error analyzing nutrition'
                    }
                }
            },

            checkHealth: async () => {
                return await apiFetch('/health')
            },

            // ============================================
            // PROACTIVE AGENT FUNCTIONS
            // ============================================

            // Load proactive interventions from backend
            loadInterventions: async () => {
                const { profile } = get()
                const userId = profile?.email || 'anonymous'

                set({ interventionsLoading: true })

                try {
                    const data = await apiFetch(`/interventions?user_id=${encodeURIComponent(userId)}`)

                    if (data && data.interventions) {
                        set({
                            interventions: data.interventions,
                            lastInterventionCheck: new Date().toISOString(),
                            interventionsLoading: false
                        })
                        return data.interventions
                    }

                    set({ interventionsLoading: false })
                    return []
                } catch (error) {
                    console.error('Error loading interventions:', error)
                    set({ interventionsLoading: false })
                    return []
                }
            },

            // Handle intervention action (dismiss, act upon)
            handleInterventionAction: async (interventionId, action) => {
                const { profile } = get()
                const userId = profile?.email || 'anonymous'

                try {
                    const result = await apiFetch(`/interventions/${interventionId}/action`, {
                        method: 'POST',
                        body: JSON.stringify({
                            user_id: userId,
                            action: action
                        })
                    })

                    if (result?.success) {
                        // Remove the intervention from the list
                        set((state) => ({
                            interventions: state.interventions.filter(i => i.id !== interventionId)
                        }))
                    }

                    return result
                } catch (error) {
                    console.error('Error handling intervention:', error)
                    return { success: false, error: error.message }
                }
            },

            // Clear all interventions
            clearInterventions: () => {
                set({ interventions: [] })
            },

            // Get unread intervention count (for notification badge)
            getUnreadInterventionCount: () => {
                const { interventions } = get()
                return interventions.filter(i => !i.dismissed).length
            }
        }),
        {
            name: 'nutriai-app',
            version: 3,
            migrate: (persistedState, version) => {
                if (version < 1) {
                    // v0 → v1: Remove stale calculations from cached messages
                    const stripCalcs = (msgs) =>
                        (msgs || []).map(m => {
                            if (m.calculations) {
                                const { calculations, ...rest } = m
                                return rest
                            }
                            return m
                        })

                    persistedState.messages = stripCalcs(persistedState.messages)
                    if (persistedState.chatHistory) {
                        persistedState.chatHistory = persistedState.chatHistory.map(chat => ({
                            ...chat,
                            messages: stripCalcs(chat.messages)
                        }))
                    }
                }
                if (version < 2) {
                    // v1 → v2: Remove stale safetyType/safetyMessage from cached messages
                    const stripSafety = (msgs) =>
                        (msgs || []).map(({ safetyType, safetyMessage, ...rest }) => rest)

                    persistedState.messages = stripSafety(persistedState.messages)
                    if (persistedState.chatHistory) {
                        persistedState.chatHistory = persistedState.chatHistory.map(chat => ({
                            ...chat,
                            messages: stripSafety(chat.messages)
                        }))
                    }
                }
                if (version < 3) {
                    // v2 → v3: Clear local chat history to fix ID mismatch bug.
                    // Old chats used timestamp IDs (Date.now()), but the server stores UUIDs.
                    // This caused deleted conversations to reappear on refresh.
                    // Conversations will be reloaded from server with correct UUID IDs.
                    persistedState.chatHistory = []
                    persistedState.messages = []
                    persistedState.currentChatId = null
                }
                return persistedState
            },
            partialize: (state) => {
                // Strip transient fields from messages before persisting
                // calculations, safetyType, safetyMessage are computed server-side per request
                const stripTransient = (msgs) =>
                    (msgs || []).map(({ calculations, safetyType, safetyMessage, ...rest }) => rest)

                return {
                    profile: state.profile,
                    messages: stripTransient(state.messages),
                    chatHistory: (state.chatHistory || []).map(chat => ({
                        ...chat,
                        messages: stripTransient(chat.messages)
                    })),
                    currentChatId: state.currentChatId
                }
            }
        }
    )
)
