/**
 * NourishGraph Chat Page
 * Enhanced with advanced features and professional UX
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useAppStore } from '../stores/appStore'
import { useToast } from '../components/ui/Toast'
import MarkdownRenderer from '../components/chat/MarkdownRenderer'
import { InlineCitations } from '../components/chat/SourcesDisplay'
import { CalculationDisplay } from '../components/chat/CalculationDisplay'
import { AgentBadgeMini, AgentBadgeProgressive } from '../components/chat/AgentBadge'
import { SafetyMessage } from '../components/chat/SafetyMessage'
import { TypingIndicator } from '../components/ui/LoadingStates'
import {
    Send, Trash2, Copy, RefreshCw,
    X, BookOpen, FileText, ExternalLink, Sparkles, CheckCircle2,
    MessageSquare, Plus, ChevronLeft, ChevronRight, Download, Clock,
    Search, Edit3, FlaskConical, Brain, Zap, Pencil, Check, Leaf, Loader2, User,
    Target, Microscope, UtensilsCrossed, BarChart3, Share2,
    Mic, MicOff, ChevronDown, Heart, ThumbsUp, ThumbsDown, Square, LayoutDashboard, Menu, History
} from 'lucide-react'
import { Link } from 'react-router-dom'

// API base URL - in production no prefix needed, in dev /api is proxied
const API_BASE = import.meta.env.PROD ? '' : '/api'

// Welcome cards - Auth style with emerald gradients
const welcomeCards = [
    {
        Icon: Target,
        title: 'Personalized Advice',
        desc: 'Recommendations based on your profile',
        text: 'What should I eat to reach my weight goal?',
        gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(52, 211, 153, 0.08) 100%)',
        iconGradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        glowColor: 'rgba(16, 185, 129, 0.3)'
    },
    {
        Icon: Microscope,
        title: 'Scientific Research',
        desc: 'Evidence-based insights',
        text: 'What does research say about intermittent fasting?',
        gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.08) 100%)',
        iconGradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        glowColor: 'rgba(16, 185, 129, 0.3)'
    },
    {
        Icon: BarChart3,
        title: 'Nutrition Analysis',
        desc: 'Track and optimize your diet',
        text: 'How many calories should I eat daily?',
        gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.08) 100%)',
        iconGradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        glowColor: 'rgba(16, 185, 129, 0.3)'
    },
    {
        Icon: UtensilsCrossed,
        title: 'Meal Planning',
        desc: 'Create balanced meal plans',
        text: 'Suggest me a healthy breakfast',

        gradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.08) 100%)',
        iconGradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        glowColor: 'rgba(16, 185, 129, 0.3)'
    },
]

function formatPendingValue(value) {
    if (value === null || value === undefined) return null
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
    if (Array.isArray(value)) return value.filter(v => v !== null && v !== undefined).map(String).join(', ')
    try {
        return JSON.stringify(value)
    } catch {
        return String(value)
    }
}

function getPendingSummary(pending) {
    if (!pending || typeof pending !== 'object') return []

    const rows = []
    const type = pending.type || pending.action || pending.kind
    if (type) rows.push(['Action', String(type)])

    const proposed = pending.proposed && typeof pending.proposed === 'object' ? pending.proposed : null
    if (proposed) {
        Object.entries(proposed)
            .filter(([, v]) => v !== null && v !== undefined && v !== '')
            .slice(0, 6)
            .forEach(([k, v]) => {
                const formatted = formatPendingValue(v)
                if (formatted) rows.push([k.replaceAll('_', ' '), formatted])
            })
    }

    return rows
}

export default function Chat() {
    const {
        messages, sources, isTyping, sendMessage, sendMessageStreaming, clearChat,
        chatHistory, currentChatId, createNewChat, switchChat, deleteChat, renameChat,
        regenerateMessage, editAndResendMessage, stopGeneration
    } = useAppStore()

    const toast = useToast()

    const [input, setInput] = useState('')
    const [showSources, setShowSources] = useState(false)
    const [showHistory, setShowHistory] = useState(true)
    const [selectedSource, setSelectedSource] = useState(null)
    const [copiedId, setCopiedId] = useState(null)
    const [editingChatId, setEditingChatId] = useState(null)
    const [editingName, setEditingName] = useState('')
    const [searchHistory, setSearchHistory] = useState('')
    const [editingMessageIndex, setEditingMessageIndex] = useState(null)
    const [editingMessageContent, setEditingMessageContent] = useState('')
    const [showScrollButton, setShowScrollButton] = useState(false)
    const [isRecording, setIsRecording] = useState(false)
    const [activeAgent, setActiveAgent] = useState(null)
    const [processingSteps, setProcessingSteps] = useState([])
    const messagesEndRef = useRef(null)
    const messagesContainerRef = useRef(null)
    const inputRef = useRef(null)

    // Mobile sources bottom sheet
    const [showMobileSources, setShowMobileSources] = useState(false)
    // Mobile history bottom sheet
    const [showMobileHistory, setShowMobileHistory] = useState(false)

    // Accumulated sources from ALL messages in session (not just the last one)
    const [allSessionSources, setAllSessionSources] = useState([])
    // View mode: 'current' or 'all'
    const [sourcesViewMode, setSourcesViewMode] = useState('current')
    // Expanded source index for details view
    const [expandedSourceIndex, setExpandedSourceIndex] = useState(null)

    // Deduplicated sources - only from the LAST assistant message
    // This ensures we show only sources relevant to the current question
    const lastAssistantMessage = [...(messages || [])].reverse().find(m => m.role === 'assistant' && m.sources?.length > 0)
    const allSources = (lastAssistantMessage?.sources || sources || [])
        .filter((s, i, arr) => s && s.title && s.title.trim() !== '' && arr.findIndex(x => x?.title === s?.title) === i)

    // Update accumulated sources whenever messages change
    useEffect(() => {
        if (messages && messages.length > 0) {
            const newSources = messages
                .filter(m => m.role === 'assistant' && m.sources?.length > 0)
                .flatMap(m => m.sources || [])
                .filter(s => s && s.title && s.title.trim() !== '')

            // Deduplicate by title
            const uniqueSources = newSources.filter((s, i, arr) =>
                arr.findIndex(x => x?.title === s?.title) === i
            )

            setAllSessionSources(uniqueSources)
        }
    }, [messages])

    // Get sources based on current view mode
    const displayedSources = sourcesViewMode === 'all' ? allSessionSources : allSources

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    // Check if any message is currently streaming
    const isStreaming = messages.some(m => m.isStreaming)

    useEffect(() => {
        scrollToBottom()
    }, [messages, isTyping, isStreaming])

    // Continuous scroll during streaming
    useEffect(() => {
        if (isStreaming) {
            const interval = setInterval(() => {
                scrollToBottom()
            }, 300) // Scroll every 300ms during streaming
            return () => clearInterval(interval)
        }
    }, [isStreaming])

    // Don't auto-show sources - let user click to open
    // useEffect(() => {
    //     if (allSources.length > 0) setShowSources(true)
    // }, [allSources.length])

    // Handle scroll position for scroll-to-bottom button
    const handleScroll = useCallback(() => {
        if (messagesContainerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current
            setShowScrollButton(scrollHeight - scrollTop - clientHeight > 200)
        }
    }, [])

    // Export conversation as markdown
    const exportConversation = () => {
        if (!messages || messages.length === 0) {
            toast.warning('No messages to export')
            return
        }
        const content = messages.map(m =>
            `${m.role === 'user' ? 'You' : 'NourishGraph'}:\n${m.content}\n`
        ).join('\n---\n\n')

        const blob = new Blob([content], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `nourishgraph-conversation-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        toast.success('Conversation exported!')
    }

    // Voice input toggle
    const toggleVoiceRecording = () => {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            toast.warning('Voice input not supported in this browser')
            return
        }
        setIsRecording(!isRecording)
        if (!isRecording) {
            toast.info('Listening...')
            setTimeout(() => {
                setIsRecording(false)
                toast.info('Voice feature coming soon!')
            }, 2000)
        }
    }

    const handleSend = async () => {
        if (!input.trim() || isTyping) return
        const msg = input.trim()
        setInput('')

        // Show processing indicator
        setActiveAgent('analyzing')
        setProcessingSteps([
            { id: 1, text: 'Analyzing your question...', status: 'active' }
        ])

        // Use streaming for real-time response display
        const result = await sendMessageStreaming(msg, {
            onIntent: (intent) => {
                // Update processing steps when intent is detected
                const agentName = intent === 'science' ? 'Science Agent'
                    : intent === 'nutrition' ? 'Nutrition Agent'
                        : intent === 'profile' ? 'Profile Agent'
                            : intent === 'meal' ? 'Meal Agent'
                                : 'Chat Agent'
                setActiveAgent(intent)
                setProcessingSteps([
                    { id: 1, text: 'Query analyzed', status: 'completed' },
                    { id: 2, text: `${agentName} responding...`, status: 'active' }
                ])
            },
            onTool: (tool) => {
                // Show tool execution feedback
                setProcessingSteps(prev => [
                    ...prev.filter(s => s.id <= 2),
                    { id: 3, text: `Using ${tool}...`, status: 'active' }
                ])
            },
            onChunk: (chunk, fullText) => {
                // Response is updating in real-time via store
                // Could add typing indicator animation here
            },
            onDone: ({ response, intent, toolsUsed, sources }) => {
                setProcessingSteps([
                    { id: 1, text: 'Query analyzed', status: 'completed' },
                    { id: 2, text: `Response complete`, status: 'completed' }
                ])
            },
            onError: (err) => {
                toast.error(`Error: ${err.message}`)
                setProcessingSteps([
                    { id: 1, text: 'Error occurred', status: 'completed' }
                ])
            }
        })

        // Clear after short delay
        setTimeout(() => {
            setActiveAgent(null)
            setProcessingSteps([])
        }, 500)
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleQuickMessage = (text) => {
        setInput(text)
        inputRef.current?.focus()
    }

    const copyMessage = (text, id) => {
        navigator.clipboard.writeText(text)
        setCopiedId(id)
        toast.success('Copied to clipboard')
        setTimeout(() => setCopiedId(null), 2000)
    }

    const handleRenameChat = (chatId) => {
        if (editingName.trim() && renameChat) {
            renameChat(chatId, editingName.trim())
        }
        setEditingChatId(null)
        setEditingName('')
    }

    const handleRegenerate = async (messageIndex) => {
        if (isTyping) return
        await regenerateMessage(messageIndex)
    }

    const handleEditMessage = (index, content) => {
        setEditingMessageIndex(index)
        setEditingMessageContent(content)
    }

    const handleSaveEdit = async () => {
        if (!editingMessageContent.trim()) return
        const content = editingMessageContent.trim()
        const index = editingMessageIndex

        // Close modal immediately
        setEditingMessageIndex(null)
        setEditingMessageContent('')

        // Stop current generation if running - this will hide the "thinking" indicator
        if (isTyping) {
            stopGeneration?.()
            // Brief pause so user sees the transition (thinking stops, then restarts)
            await new Promise(resolve => setTimeout(resolve, 300))
        }

        // Now send the edited message - this will show "thinking" again
        await editAndResendMessage(index, content)
    }

    const handleCancelEdit = () => {
        setEditingMessageIndex(null)
        setEditingMessageContent('')
    }

    // Enhanced markdown formatting
    const formatMessage = (text) => {
        if (!text) return ''
        return text
            .replace(/^### (.+)$/gm, '<h4 class="text-sm font-bold text-primary-600 dark:text-primary-400 mt-4 mb-2 flex items-center gap-2">› $1</h4>')
            .replace(/^## (.+)$/gm, '<h3 class="text-base font-bold mt-5 mb-3 pb-2 border-b border-neutral-200 dark:border-neutral-700">$1</h3>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-text-primary font-semibold">$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em class="text-text-secondary">$1</em>')
            .replace(/^(\d+)\.\s+\*\*([^*:]+)\*\*:?\s*/gm, '</p><div class="my-3 p-3 bg-hover rounded-lg border-l-2 border-primary-500"><div class="flex items-start gap-3"><span class="w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center shrink-0 text-white" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%)">$1</span><div><strong class="text-text-primary font-semibold block mb-1">$2</strong><span class="text-text-secondary text-sm">')
            .replace(/^(\d+)\.\s+(.+)$/gm, '<div class="my-2 flex items-start gap-3"><span class="w-5 h-5 rounded text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 text-white" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%)">$1</span><span>$2</span></div>')
            .replace(/^[•\-]\s+(.+)$/gm, '<div class="my-1.5 flex items-start gap-2 pl-2"><span class="text-primary-500">›</span><span>$1</span></div>')
            .replace(/\n\n/g, '</span></div></div></p><p class="my-3">')
            .replace(/\n/g, '<br>')
    }

    const showWelcome = !messages || messages.length === 0

    // Filter chat history by search
    const filteredHistory = (chatHistory || []).filter(chat =>
        !searchHistory || chat.name?.toLowerCase().includes(searchHistory.toLowerCase())
    )

    return (
        <div className="h-full flex relative" style={{ background: 'var(--color-bg-primary)', overflow: 'hidden' }}>
            {/* Chat History Sidebar - Hidden on mobile */}
            <div className={`hidden md:flex transition-all duration-300 flex-col ${showHistory ? 'w-72' : 'w-0 overflow-hidden'}`} style={{ background: 'var(--color-bg-secondary)', borderRight: '1px solid var(--color-border)' }}>
                <div className="w-72 flex flex-col h-full">
                    {/* Sidebar Header */}
                    <div className="p-4">
                        <button
                            onClick={() => createNewChat?.()}
                            className="w-full flex items-center justify-center gap-2.5 px-4 py-3.5 text-white rounded-xl font-semibold transition-all hover:scale-[1.02] active:scale-[0.98]"
                            style={{
                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)'
                            }}
                        >
                            <Plus className="w-5 h-5" style={{ color: '#ffffff' }} />
                            <span style={{ color: '#ffffff' }}>New Chat</span>
                        </button>
                    </div>

                    {/* Search */}
                    <div className="px-4 pb-3">
                        <div className="relative group">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors" style={{ color: 'var(--color-text-muted)' }} />
                            <input
                                type="text"
                                placeholder="Search..."
                                value={searchHistory}
                                onChange={(e) => setSearchHistory(e.target.value)}
                                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm focus:outline-none transition-all"
                                style={{
                                    background: 'var(--color-input-bg)',
                                    border: '1px solid var(--color-border)',
                                    color: 'var(--color-text-primary)'
                                }}
                            />
                        </div>
                    </div>

                    {/* Chat List */}
                    <div className="flex-1 overflow-y-auto px-3">
                        {filteredHistory.filter(chat => chat.messages?.length > 0).length === 0 ? (
                            <div className="text-center py-12 px-4">
                                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--color-bg-elevated)' }}>
                                    <MessageSquare className="w-7 h-7" style={{ color: 'var(--color-text-muted)' }} />
                                </div>
                                <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>No conversations yet</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Start chatting to see your history</p>
                            </div>
                        ) : (
                            <div className="space-y-1.5 py-2">
                                {filteredHistory.filter(chat => chat.messages?.length > 0 || chat.id === currentChatId).map((chat) => (
                                    <div
                                        key={chat.id}
                                        className="group relative flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all"
                                        style={currentChatId === chat.id
                                            ? { background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)' }
                                            : { border: '1px solid transparent' }
                                        }
                                        onClick={() => switchChat?.(chat.id)}
                                    >
                                        <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                                            style={currentChatId === chat.id
                                                ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }
                                                : { background: 'var(--color-bg-elevated)' }
                                            }>
                                            <MessageSquare className="w-4 h-4" style={{ color: currentChatId === chat.id ? '#ffffff' : 'var(--color-text-muted)' }} />
                                        </div>

                                        {editingChatId === chat.id ? (
                                            <div className="flex-1 flex items-center gap-1">
                                                <input
                                                    type="text"
                                                    value={editingName}
                                                    onChange={(e) => setEditingName(e.target.value)}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter') handleRenameChat(chat.id)
                                                        if (e.key === 'Escape') setEditingChatId(null)
                                                    }}
                                                    className="flex-1 bg-transparent text-sm focus:outline-none py-1"
                                                    style={{ borderBottom: '2px solid #10B981', color: 'var(--color-text-primary)' }}
                                                    autoFocus
                                                    onClick={(e) => e.stopPropagation()}
                                                />
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleRenameChat(chat.id)
                                                    }}
                                                    className="p-1 rounded-md transition-colors hover:bg-green-500/20"
                                                    title="Confirm"
                                                >
                                                    <Check className="w-4 h-4" style={{ color: '#10B981' }} />
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        setEditingChatId(null)
                                                    }}
                                                    className="p-1 rounded-md transition-colors hover:bg-red-500/20"
                                                    title="Cancel"
                                                >
                                                    <X className="w-4 h-4" style={{ color: '#ef4444' }} />
                                                </button>
                                            </div>
                                        ) : (
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate" style={{ color: currentChatId === chat.id ? '#10B981' : 'var(--color-text-primary)' }}>
                                                    {chat.name || 'New Conversation'}
                                                </p>
                                                {chat.messages?.length > 0 && (
                                                    <p className="text-[10px] truncate mt-0.5" style={{ color: currentChatId === chat.id ? '#10B981' : 'var(--color-text-muted)' }}>
                                                        {chat.messages.length} message{chat.messages.length !== 1 ? 's' : ''}
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {/* Actions */}
                                        <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex gap-0.5 transition-opacity rounded-lg p-0.5" style={{ background: 'var(--color-bg-elevated)' }}>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    setEditingChatId(chat.id)
                                                    setEditingName(chat.name || '')
                                                }}
                                                className="p-1.5 rounded-md transition-colors hover:bg-white/10"
                                                title="Rename"
                                            >
                                                <Edit3 className="w-3.5 h-3.5" style={{ color: 'var(--color-text-muted)' }} />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    deleteChat?.(chat.id)
                                                }}
                                                className="p-1.5 rounded-md transition-colors hover:bg-red-500/20"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" style={{ color: 'var(--color-text-muted)' }} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Sidebar Footer */}
                    <div className="p-3 flex items-center justify-between" style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-bg-secondary)' }}>
                        <button
                            onClick={() => {
                                clearChat()
                                toast.success('All conversations cleared')
                            }}
                            disabled={chatHistory.filter(c => c.messages?.length > 0).length === 0}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            style={{ color: '#F87171' }}
                        >
                            <Trash2 className="w-4 h-4" />
                            Clear All
                        </button>
                    </div>
                </div>
            </div>

            {/* Toggle History Button - Hidden on mobile */}
            <button
                onClick={() => setShowHistory(!showHistory)}
                className={`hidden md:flex absolute top-1/2 -translate-y-1/2 z-10 w-6 h-14 rounded-r-xl items-center justify-center transition-all shadow-sm ${showHistory ? 'left-72' : 'left-0'}`}
                style={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', borderLeft: 'none', color: 'var(--color-text-muted)' }}
            >
                {showHistory ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0 min-h-0">
                {/* Messages Area */}
                <div className={`flex-1 overflow-y-auto px-3 sm:px-4 py-4 sm:py-6`} ref={messagesContainerRef} onScroll={handleScroll}>
                    {showWelcome ? (
                        /* Welcome Screen - Scrollable on small screens */
                        <div className="min-h-full flex flex-col items-center justify-center px-2 sm:px-8">
                            <div className="max-w-3xl w-full text-center py-4 sm:py-0">
                                {/* Logo/Title */}
                                <div className="mb-3 sm:mb-12">
                                    <div className="relative inline-block">
                                        <div className="absolute inset-0 rounded-3xl blur-2xl animate-pulse" style={{ background: 'rgba(16, 185, 129, 0.25)' }} />
                                        <div className="relative w-10 h-10 sm:w-20 sm:h-20 rounded-xl sm:rounded-3xl flex items-center justify-center mx-auto mb-1.5 sm:mb-6 shadow-2xl"
                                            style={{
                                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                                boxShadow: '0 25px 50px rgba(16, 185, 129, 0.3)'
                                            }}>
                                            <Leaf className="w-5 h-5 sm:w-10 sm:h-10" style={{ color: '#ffffff' }} />
                                        </div>
                                    </div>
                                    <h1 className="text-lg sm:text-3xl font-bold mb-0.5 sm:mb-3 font-display">
                                        <span style={{ color: 'var(--color-text-primary)' }}>Welcome to </span>
                                        <span style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>NourishGraph</span>
                                    </h1>
                                    <p style={{ color: 'var(--color-text-muted)' }} className="text-[11px] sm:text-base max-w-lg mx-auto leading-relaxed">
                                        Your AI-powered nutrition assistant with science-based insights
                                    </p>
                                </div>

                                {/* Feature Cards - Smaller on mobile, scrollable */}
                                <div className="grid grid-cols-2 gap-1.5 sm:gap-6 max-w-2xl mx-auto stagger-children">
                                    {welcomeCards.map((card, i) => (
                                        <button
                                            key={i}
                                            onClick={() => handleQuickMessage(card.text)}
                                            className="group relative overflow-hidden p-2.5 sm:p-6 rounded-lg sm:rounded-2xl text-left transition-all duration-300 hover:scale-[1.03] hover:-translate-y-2 card-3d"
                                            style={{
                                                background: 'var(--color-bg-elevated)',
                                                border: '1px solid var(--color-border)',
                                                boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
                                            }}
                                        >
                                            {/* Hover effect */}
                                            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                                                style={{ background: card.gradient }} />

                                            {/* Glow effect on hover */}
                                            <div className="absolute -inset-1 opacity-0 group-hover:opacity-100 rounded-2xl blur-xl transition-opacity duration-500"
                                                style={{ background: card.glowColor }} />

                                            <div className="relative">
                                                <div className="w-8 h-8 sm:w-14 sm:h-14 rounded-lg sm:rounded-xl flex items-center justify-center mb-1.5 sm:mb-4 shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"
                                                    style={{ background: card.iconGradient, boxShadow: `0 8px 24px ${card.glowColor}` }}>
                                                    <card.Icon className="w-4 h-4 sm:w-7 sm:h-7" style={{ color: '#ffffff' }} />
                                                </div>
                                                <h3 className="font-semibold text-xs sm:text-lg mb-0 sm:mb-1 leading-tight" style={{ color: 'var(--color-text-primary)' }}>{card.title}</h3>
                                                <p className="text-[10px] sm:text-sm leading-tight" style={{ color: 'var(--color-text-muted)' }}>{card.desc}</p>
                                            </div>
                                        </button>
                                    ))}
                                </div>

                            </div>
                        </div>
                    ) : (
                        /* Messages */
                        <div className="max-w-3xl mx-auto space-y-4 sm:space-y-6">
                            {messages
                                .filter(msg => {
                                    // Hide empty streaming messages
                                    if (msg.isStreaming && !msg.content?.trim()) return false
                                    // Hide empty finalized assistant messages (orphaned from errors)
                                    if (msg.role === 'assistant' && !msg.isStreaming && !msg.content?.trim()) return false
                                    return true
                                })
                                .map((msg, i) => (
                                    <div
                                        key={i}
                                        className={`flex gap-2 sm:gap-3 animate-fadeIn ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                                    >
                                        {/* Avatar */}
                                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 shadow-md"
                                            style={msg.role === 'user'
                                                ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)' }
                                                : { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)' }
                                            }>
                                            {msg.role === 'user' ? <User className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: '#ffffff' }} /> : <Leaf className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: '#ffffff' }} />}
                                        </div>

                                        {/* Content */}
                                        <div className={`flex-1 max-w-[90%] sm:max-w-[80%] ${msg.role === 'user' ? 'text-right' : ''}`}>
                                            {/* Role label with agent info - combined in one line */}
                                            <div className={`flex items-center gap-2 mb-1.5 flex-wrap ${msg.role === 'user' ? 'justify-end' : ''}`}>
                                                <span className="text-[10px] font-semibold uppercase tracking-wider"
                                                    style={{ color: msg.role === 'user' ? '#10B981' : 'var(--color-text-muted)' }}>
                                                    {msg.role === 'user' ? 'You' : 'NourishGraph'}
                                                </span>
                                                {/* Agent Badge inline with name */}
                                                {msg.role === 'assistant' && !msg.isStreaming && msg.content?.trim() && (
                                                    <AgentBadgeMini
                                                        intent={msg.intent}
                                                        sources={msg.sources}
                                                    />
                                                )}
                                            </div>

                                            <div className={`inline-block px-4 py-3 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
                                                ? 'text-white rounded-br-md'
                                                : 'rounded-bl-md text-left w-full shadow-sm'
                                                }`}
                                                style={msg.role === 'user'
                                                    ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 8px 25px rgba(16, 185, 129, 0.25)' }
                                                    : { background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }
                                                }>
                                                {msg.role === 'user' ? (
                                                    editingMessageIndex === i ? (
                                                        <div className="flex flex-col gap-3 text-left">
                                                            <textarea
                                                                value={editingMessageContent}
                                                                onChange={(e) => setEditingMessageContent(e.target.value)}
                                                                className="w-full px-3 py-2 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-emerald-300"
                                                                style={{ 
                                                                    background: '#ffffff',
                                                                    color: '#111827',
                                                                    border: '2px solid #d1d5db',
                                                                    fontSize: '15px',
                                                                    lineHeight: '1.5',
                                                                    caretColor: '#111827',
                                                                    WebkitTextFillColor: '#111827',
                                                                }}
                                                                spellCheck={false}
                                                                rows={3}
                                                                autoFocus
                                                            />
                                                            <div className="flex gap-2 justify-end items-center">
                                                                <button
                                                                    onClick={handleCancelEdit}
                                                                    className="px-4 py-2 text-xs rounded-lg transition-colors"
                                                                    style={{ background: 'rgba(0, 0, 0, 0.2)', color: '#ffffff' }}
                                                                >
                                                                    Cancel
                                                                </button>
                                                                <button
                                                                    onClick={handleSaveEdit}
                                                                    disabled={!editingMessageContent.trim()}
                                                                    className="px-4 py-2 text-xs rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50 font-semibold"
                                                                    style={{ background: 'rgba(255, 255, 255, 0.25)', color: '#ffffff' }}
                                                                >
                                                                    <Send className="w-3.5 h-3.5" />
                                                                    Resend
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <p className="whitespace-pre-wrap" style={{ color: '#ffffff' }}>{msg.content}</p>
                                                    )
                                                ) : (
                                                    <>
                                                        {/* Error indicator */}
                                                        {msg.isError && (
                                                            <div className="flex items-center gap-2 mb-3 pb-3" style={{ borderBottom: '1px solid rgba(239, 68, 68, 0.2)' }}>
                                                                <div className="w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                                                                    <span className="text-red-500 text-xs font-bold">!</span>
                                                                </div>
                                                                <span className="text-xs font-medium text-red-500">
                                                                    Something went wrong
                                                                </span>
                                                            </div>
                                                        )}
                                                        {/* Safety Message - for medical/medication queries */}
                                                        {msg.safetyType && (
                                                            <SafetyMessage
                                                                type={msg.safetyType}
                                                                customMessage={msg.safetyMessage}
                                                                className="mb-3"
                                                            />
                                                        )}
                                                        {/* Use new MarkdownRenderer */}
                                                        <MarkdownRenderer content={msg.content} />
                                                        {/* Streaming cursor indicator */}
                                                        {msg.isStreaming && (
                                                            <span className="inline-block w-2 h-4 bg-primary-500 animate-pulse ml-1 rounded-sm" />
                                                        )}
                                                        {/* Retry button for errors */}
                                                        {msg.isError && (
                                                            <button
                                                                onClick={() => handleRegenerate(i)}
                                                                disabled={isTyping}
                                                                className="mt-3 flex items-center gap-2 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm font-medium hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
                                                            >
                                                                <RefreshCw className={`w-4 h-4 ${isTyping ? 'animate-spin' : ''}`} />
                                                                Try Again
                                                            </button>
                                                        )}
                                                    </>
                                                )}
                                            </div>

                                            {/* Inline Citations - ChatGPT/Claude style */}
                                            {msg.role === 'assistant' && msg.sources?.length > 0 && (
                                                <InlineCitations
                                                    sources={msg.sources}
                                                    onSourceClick={(index) => {
                                                        // Find the matching source in displayedSources
                                                        const clickedSource = msg.sources[index]
                                                        const displayIndex = displayedSources.findIndex(
                                                            s => s.title === clickedSource?.title
                                                        )
                                                        setShowSources(true)
                                                        setShowMobileSources(true)
                                                        setExpandedSourceIndex(displayIndex >= 0 ? displayIndex : index)
                                                    }}
                                                />
                                            )}

                                            {/* NEW: Calculation Display (for nutrition queries) */}
                                            {msg.role === 'assistant' && msg.calculations && (
                                                <CalculationDisplay calculations={msg.calculations} />
                                            )}

                                            {/* Actions for user messages - Edit button */}
                                            {msg.role === 'user' && editingMessageIndex !== i && (
                                                <div className="flex items-center gap-1 mt-2 justify-end">
                                                    <button
                                                        onClick={() => handleEditMessage(i, msg.content)}
                                                        className="p-1.5 rounded-lg text-text-muted hover:bg-hover hover:text-text-primary transition-all"
                                                        title="Edit message"
                                                    >
                                                        <Pencil className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            )}

                                            {/* Actions for assistant messages */}
                                            {msg.role === 'assistant' && (
                                                <div className="flex items-center gap-1 mt-2">
                                                    <button
                                                        onClick={() => copyMessage(msg.content, i)}
                                                        className={`p-1.5 rounded-lg transition-all ${copiedId === i
                                                            ? 'text-success bg-success/10'
                                                            : 'text-text-muted hover:bg-hover hover:text-text-primary'
                                                            }`}
                                                        title="Copy"
                                                    >
                                                        {copiedId === i ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                                    </button>
                                                    <button
                                                        onClick={() => handleRegenerate(i)}
                                                        disabled={isTyping}
                                                        className="p-1.5 rounded-lg text-text-muted hover:bg-hover hover:text-text-primary transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                                        title="Regenerate"
                                                    >
                                                        <RefreshCw className={`w-4 h-4 ${isTyping ? 'animate-spin' : ''}`} />
                                                    </button>
                                                </div>
                                            )}

                                            {/* Confirmation gate actions */}
                                            {msg.role === 'assistant' && msg.requiresConfirmation && (
                                                <div className="mt-4">
                                                    {Array.isArray(getPendingSummary(msg.pending)) && getPendingSummary(msg.pending).length > 0 && (
                                                        <div
                                                            className="mb-4 p-4 rounded-2xl shadow-sm"
                                                            style={{
                                                                background: 'var(--color-bg-card)',
                                                                border: '1px solid rgba(16, 185, 129, 0.2)'
                                                            }}
                                                        >
                                                            <div className="flex items-center gap-2 mb-3">
                                                                <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                                                                    <Clock className="w-3.5 h-3.5" style={{ color: '#10B981' }} />
                                                                </div>
                                                                <span className="text-sm font-semibold" style={{ color: '#10B981' }}>
                                                                    Pending Confirmation
                                                                </span>
                                                            </div>
                                                            <div className="space-y-2 pl-8">
                                                                {getPendingSummary(msg.pending).map(([k, v]) => (
                                                                    <div key={`${k}:${v}`} className="flex items-center gap-2 text-sm py-1 px-3 rounded-lg" style={{ background: 'var(--color-bg-secondary)' }}>
                                                                        <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>{k}:</span>
                                                                        <span style={{ color: 'var(--color-text-secondary)' }}>{v}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <div className="flex items-center gap-3 mt-2">
                                                        <button
                                                            onClick={() => sendMessage('CONFIRM')}
                                                            disabled={isTyping}
                                                            className="px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98] shadow-lg"
                                                            style={{
                                                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                                                color: 'white',
                                                                boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                                                            }}
                                                        >
                                                            Confirm
                                                        </button>
                                                        <button
                                                            onClick={() => sendMessage('CANCEL')}
                                                            disabled={isTyping}
                                                            className="px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98]"
                                                            style={{
                                                                background: 'var(--color-bg-secondary)',
                                                                border: '1px solid var(--color-border)',
                                                                color: 'var(--color-text-secondary)',
                                                            }}
                                                        >
                                                            Cancel
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}

                            {/* Typing Indicator */}
                            {isTyping && (
                                <TypingIndicator agentName="NutriBot" className="animate-fadeIn" />
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="shrink-0 backdrop-blur-2xl p-2 sm:p-4" style={{ borderTop: '1px solid var(--color-border)', background: 'var(--color-bg-card)' }}>
                    <div className="max-w-3xl mx-auto">
                        <div className="relative group">
                            <div className="absolute -inset-0.5 rounded-xl sm:rounded-2xl blur opacity-0 group-focus-within:opacity-100 transition-opacity" style={{ background: 'linear-gradient(135deg, rgba(0, 217, 165, 0.2) 0%, rgba(14, 165, 233, 0.2) 100%)' }} />
                            <div className="relative flex gap-2 sm:gap-3 items-end rounded-xl sm:rounded-2xl p-1.5 sm:p-2 transition-colors" style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
                                <textarea
                                    ref={inputRef}
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Ask about nutrition..."
                                    rows={1}
                                    className="flex-1 px-3 sm:px-4 py-2 sm:py-3 bg-transparent resize-none focus:outline-none text-sm sm:text-base"
                                    style={{ minHeight: '44px', maxHeight: '120px', caretColor: '#10B981', color: 'var(--color-text-primary)' }}
                                />
                                <div className="flex items-center gap-1.5 sm:gap-2 pr-1 sm:pr-2">
                                    {/* Sources button - integrated */}
                                    {allSessionSources.length > 0 && (
                                        <button
                                            onClick={() => {
                                                // Desktop: toggle sidebar, Mobile: open bottom sheet
                                                if (window.innerWidth >= 1024) {
                                                    setShowSources(!showSources)
                                                } else {
                                                    setShowMobileSources(true)
                                                }
                                            }}
                                            className="relative w-9 h-9 sm:w-11 sm:h-11 rounded-lg sm:rounded-xl flex items-center justify-center transition-all hover:scale-105"
                                            style={{
                                                background: showSources ? 'linear-gradient(135deg, #10B981 0%, #059669 100%)' : 'var(--color-bg-elevated)',
                                                border: showSources ? 'none' : '1px solid var(--color-border)'
                                            }}
                                            title="Scientific sources"
                                        >
                                            <BookOpen className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: showSources ? '#ffffff' : 'var(--color-text-muted)' }} />
                                            <span
                                                className="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full text-[10px] font-bold flex items-center justify-center px-1"
                                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#ffffff' }}
                                            >
                                                {allSessionSources.length}
                                            </span>
                                        </button>
                                    )}
                                    {isTyping ? (
                                        <button
                                            onClick={() => {
                                                console.log('Stop clicked')
                                                stopGeneration()
                                            }}
                                            className="relative w-9 h-9 sm:w-11 sm:h-11 rounded-lg sm:rounded-xl flex items-center justify-center transition-all overflow-hidden hover:scale-105"
                                            style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)' }}
                                            title="Stop generating"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="#ffffff" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                            </svg>
                                        </button>
                                    ) : (
                                        <button
                                            onClick={handleSend}
                                            disabled={!input.trim()}
                                            className="relative w-9 h-9 sm:w-11 sm:h-11 rounded-lg sm:rounded-xl flex items-center justify-center transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none overflow-hidden group/btn"
                                            style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)' }}
                                        >
                                            <Send className="w-4 h-4 sm:w-5 sm:h-5 relative z-10" style={{ color: '#ffffff' }} />
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>



                        {/* Mobile Bottom Navigation */}
                        <div className="md:hidden flex items-center justify-around mt-2 pt-2" style={{ borderTop: '1px solid var(--color-border)' }}>
                            <button
                                onClick={() => setShowMobileHistory(true)}
                                className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                <History className="w-4 h-4" />
                                <span className="text-[9px] font-medium">Chats</span>
                            </button>

                            <button
                                onClick={() => createNewChat?.()}
                                className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all"
                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: 'white' }}
                            >
                                <Plus className="w-4 h-4" />
                                <span className="text-[9px] font-medium">New</span>
                            </button>

                            <Link
                                to="/"
                                className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all"
                                style={{ color: 'var(--color-text-muted)' }}
                            >
                                <LayoutDashboard className="w-4 h-4" />
                                <span className="text-[9px] font-medium">Dashboard</span>
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            {/* Sources Panel - Hidden on mobile */}
            <div className={`hidden lg:flex transition-all duration-300 flex-col ${showSources ? 'w-80' : 'w-0 overflow-hidden'}`} style={{ background: 'var(--color-bg-card)', borderLeft: '1px solid var(--color-border)' }}>
                <div className="w-80 flex flex-col h-full">
                    {/* Header */}
                    <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
                        <h3 className="font-semibold flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                            <BookOpen className="w-4 h-4" style={{ color: '#10B981' }} />
                            Scientific Sources
                            {displayedSources.length > 0 && (
                                <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' }}>
                                    {displayedSources.length}
                                </span>
                            )}
                        </h3>
                        <button
                            onClick={() => setShowSources(false)}
                            className="p-1.5 rounded-lg transition-all"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Toggle: Current vs All Session Sources - only show if there are more sources in session than current */}
                    {allSessionSources.length > allSources.length && (
                        <div className="px-3 pt-3">
                            <div className="flex rounded-lg p-1" style={{ background: 'var(--color-bg-secondary)' }}>
                                <button
                                    onClick={() => { setSourcesViewMode('current'); setExpandedSourceIndex(null); }}
                                    className="flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all"
                                    style={sourcesViewMode === 'current' ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' } : { color: 'var(--color-text-muted)' }}
                                >
                                    Current ({allSources.length})
                                </button>
                                <button
                                    onClick={() => { setSourcesViewMode('all'); setExpandedSourceIndex(null); }}
                                    className="flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all"
                                    style={sourcesViewMode === 'all' ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' } : { color: 'var(--color-text-muted)' }}
                                >
                                    All Session ({allSessionSources.length})
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Sources List */}
                    <div className="flex-1 overflow-y-auto p-3">
                        {displayedSources.length === 0 ? (
                            <div className="text-center py-12">
                                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--color-bg-elevated)' }}>
                                    <FlaskConical className="w-7 h-7" style={{ color: 'var(--color-text-muted)' }} />
                                </div>
                                <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>No sources yet</p>
                                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Ask about nutrition science to see papers</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {displayedSources.map((src, i) => (
                                    <div
                                        key={`${src.title}-${i}`}
                                        className="p-3 rounded-xl cursor-pointer transition-all"
                                        style={expandedSourceIndex === i
                                            ? { background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)' }
                                            : { background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }
                                        }
                                        onClick={() => setExpandedSourceIndex(expandedSourceIndex === i ? null : i)}
                                    >
                                        {/* Header */}
                                        <div className="flex gap-2 mb-2">
                                            <span className="w-5 h-5 rounded text-xs font-bold flex items-center justify-center shrink-0"
                                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#ffffff' }}>
                                                {i + 1}
                                            </span>
                                            <h4 className="text-xs font-semibold leading-tight line-clamp-2" style={{ color: 'var(--color-text-primary)' }}>
                                                {src.title || 'Scientific Paper'}
                                            </h4>
                                        </div>

                                        {/* Meta */}
                                        <div className="flex flex-wrap gap-1.5 mb-2 ml-7">
                                            {src.source && (
                                                <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}>
                                                    {src.source}
                                                </span>
                                            )}
                                            {src.year && (
                                                <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}>
                                                    {src.year}
                                                </span>
                                            )}
                                        </div>

                                        {/* Expanded */}
                                        {expandedSourceIndex === i && (
                                            <div className="mt-3 pt-3 ml-7 animate-fadeIn" style={{ borderTop: '1px solid var(--color-border)' }}>
                                                {/* Authors */}
                                                {src.authors?.length > 0 && (
                                                    <p className="text-[10px] mb-2" style={{ color: 'var(--color-text-muted)' }}>
                                                        {src.authors.slice(0, 3).join(', ')}{src.authors.length > 3 ? ' et al.' : ''}
                                                    </p>
                                                )}

                                                {/* Snippet/Text from the paper */}
                                                {(src.snippet || src.text || src.abstract) && (
                                                    <p className="text-xs mb-3 leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                                                        {src.snippet || src.text || src.abstract}
                                                    </p>
                                                )}

                                                {/* Paper name */}
                                                {src.paper && (
                                                    <p className="text-[10px] mb-2 italic" style={{ color: 'var(--color-text-muted)' }}>
                                                        From: {src.paper}
                                                    </p>
                                                )}

                                                {/* Download Paper Button */}
                                                {(src.filename || src.source || src.paper) && (
                                                    <a
                                                        href={`${API_BASE}/download-paper/${encodeURIComponent(src.filename || src.source || src.paper)}`}
                                                        download
                                                        onClick={(e) => e.stopPropagation()}
                                                        className="inline-flex items-center gap-1.5 px-3 py-1.5 mt-2 rounded-lg text-xs font-medium transition-all hover:scale-105"
                                                        style={{
                                                            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                                            color: 'white'
                                                        }}
                                                    >
                                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                        </svg>
                                                        Download Paper
                                                    </a>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Mobile Sources Bottom Sheet */}
            {showMobileSources && (
                <div className="lg:hidden fixed inset-0 z-[100]">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
                        onClick={() => setShowMobileSources(false)}
                    />

                    {/* Bottom Sheet */}
                    <div
                        className="absolute bottom-0 left-0 right-0 rounded-t-3xl animate-slideUp"
                        style={{
                            background: 'var(--color-bg-card)',
                            maxHeight: '85vh'
                        }}
                    >
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className="w-12 h-1.5 rounded-full" style={{ background: 'var(--color-border)' }} />
                        </div>

                        {/* Header */}
                        <div className="flex items-center justify-between px-5 pb-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <h3 className="font-semibold text-lg flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                                <BookOpen className="w-5 h-5" style={{ color: '#10B981' }} />
                                Scientific Sources
                                <span className="px-2.5 py-1 rounded-full text-xs font-bold"
                                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' }}>
                                    {displayedSources.length}
                                </span>
                            </h3>
                            <button
                                onClick={() => setShowMobileSources(false)}
                                className="p-2 rounded-xl transition-all"
                                style={{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-muted)' }}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Toggle: Current vs All Session Sources - only show if there are more sources in session than current */}
                        {allSessionSources.length > allSources.length && (
                            <div className="px-4 pt-4">
                                <div className="flex rounded-xl p-1" style={{ background: 'var(--color-bg-secondary)' }}>
                                    <button
                                        onClick={() => { setSourcesViewMode('current'); setExpandedSourceIndex(null); }}
                                        className="flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all"
                                        style={sourcesViewMode === 'current' ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' } : { color: 'var(--color-text-muted)' }}
                                    >
                                        Current ({allSources.length})
                                    </button>
                                    <button
                                        onClick={() => { setSourcesViewMode('all'); setExpandedSourceIndex(null); }}
                                        className="flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all"
                                        style={sourcesViewMode === 'all' ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#FFFFFF' } : { color: 'var(--color-text-muted)' }}
                                    >
                                        All Session ({allSessionSources.length})
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Sources List */}
                        <div className="overflow-y-auto p-4" style={{ maxHeight: 'calc(85vh - 180px)' }}>
                            {displayedSources.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--color-bg-elevated)' }}>
                                        <FlaskConical className="w-7 h-7" style={{ color: 'var(--color-text-muted)' }} />
                                    </div>
                                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>No sources yet</p>
                                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Ask about nutrition science to see papers</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {displayedSources.map((src, i) => (
                                        <div
                                            key={`mobile-${src.title}-${i}`}
                                            className="p-4 rounded-2xl transition-all"
                                            style={expandedSourceIndex === i
                                                ? { background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)' }
                                                : { background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }
                                            }
                                            onClick={() => setExpandedSourceIndex(expandedSourceIndex === i ? null : i)}
                                        >
                                            {/* Header */}
                                            <div className="flex gap-3 mb-2">
                                                <span className="w-6 h-6 rounded-lg text-xs font-bold flex items-center justify-center shrink-0"
                                                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', color: '#ffffff' }}>
                                                    {i + 1}
                                                </span>
                                                <h4 className="text-sm font-semibold leading-tight" style={{ color: 'var(--color-text-primary)' }}>
                                                    {src.title || 'Scientific Paper'}
                                                </h4>
                                            </div>

                                            {/* Meta */}
                                            <div className="flex flex-wrap gap-2 mb-2 ml-9">
                                                {src.source && (
                                                    <span className="px-2 py-1 rounded-lg text-xs" style={{ background: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}>
                                                        {src.source}
                                                    </span>
                                                )}
                                                {src.year && (
                                                    <span className="px-2 py-1 rounded-lg text-xs" style={{ background: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}>
                                                        {src.year}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Expanded Content */}
                                            {expandedSourceIndex === i && (
                                                <div className="mt-3 pt-3 ml-9 animate-fadeIn" style={{ borderTop: '1px solid var(--color-border)' }}>
                                                    {/* Authors */}
                                                    {src.authors?.length > 0 && (
                                                        <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
                                                            {src.authors.slice(0, 3).join(', ')}{src.authors.length > 3 ? ' et al.' : ''}
                                                        </p>
                                                    )}

                                                    {/* Snippet/Text from the paper */}
                                                    {(src.snippet || src.text || src.abstract) && (
                                                        <p className="text-sm mb-3 leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                                                            {src.snippet || src.text || src.abstract}
                                                        </p>
                                                    )}

                                                    {/* Download Paper Button */}
                                                    {(src.filename || src.source || src.paper) && (
                                                        <a
                                                            href={`${API_BASE}/download-paper/${encodeURIComponent(src.filename || src.source || src.paper)}`}
                                                            download
                                                            onClick={(e) => e.stopPropagation()}
                                                            className="inline-flex items-center gap-2 px-4 py-2.5 mt-2 rounded-xl text-sm font-medium transition-all active:scale-95"
                                                            style={{
                                                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                                                color: 'white'
                                                            }}
                                                        >
                                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                            </svg>
                                                            Download Paper
                                                        </a>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Mobile History Bottom Sheet */}
            {showMobileHistory && (
                <div className="md:hidden fixed inset-0 z-50">
                    {/* Backdrop */}
                    <div
                        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
                        onClick={() => setShowMobileHistory(false)}
                    />

                    {/* Bottom Sheet */}
                    <div
                        className="absolute bottom-0 left-0 right-0 rounded-t-3xl animate-slideUp"
                        style={{
                            background: 'var(--color-bg-card)',
                            maxHeight: '85vh'
                        }}
                    >
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className="w-12 h-1.5 rounded-full" style={{ background: 'var(--color-border)' }} />
                        </div>

                        {/* Header */}
                        <div className="flex items-center justify-between px-5 pb-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
                            <h3 className="font-semibold text-lg flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
                                <History className="w-5 h-5" style={{ color: '#10B981' }} />
                                Chat History
                                <span className="px-2.5 py-1 rounded-full text-xs font-bold text-white"
                                    style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}>
                                    {chatHistory.filter(c => c.messages?.length > 0).length}
                                </span>
                            </h3>
                            <button
                                onClick={() => setShowMobileHistory(false)}
                                className="p-2 rounded-xl transition-all"
                                style={{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-muted)' }}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* New Chat Button */}
                        <div className="px-4 pt-4">
                            <button
                                onClick={() => {
                                    createNewChat?.()
                                    setShowMobileHistory(false)
                                }}
                                className="w-full flex items-center justify-center gap-2.5 px-4 py-3.5 text-white rounded-xl font-semibold transition-all active:scale-[0.98]"
                                style={{
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                    boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                <Plus className="w-5 h-5" />
                                <span>New Chat</span>
                            </button>
                        </div>

                        {/* Chat List */}
                        <div className="overflow-y-auto p-4" style={{ maxHeight: 'calc(85vh - 200px)' }}>
                            {chatHistory.filter(chat => chat.messages?.length > 0).length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--color-bg-elevated)' }}>
                                        <MessageSquare className="w-7 h-7" style={{ color: 'var(--color-text-muted)' }} />
                                    </div>
                                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>No conversations yet</p>
                                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Start chatting to see your history</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {chatHistory.filter(chat => chat.messages?.length > 0).map((chat) => (
                                        <div
                                            key={chat.id}
                                            className="flex items-center gap-3 p-4 rounded-2xl transition-all active:scale-[0.98]"
                                            style={currentChatId === chat.id
                                                ? { background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)' }
                                                : { background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }
                                            }
                                            onClick={() => {
                                                switchChat?.(chat.id)
                                                setShowMobileHistory(false)
                                            }}
                                        >
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                                                style={currentChatId === chat.id
                                                    ? { background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }
                                                    : { background: 'var(--color-bg-elevated)' }
                                                }>
                                                <MessageSquare className="w-5 h-5" style={{ color: currentChatId === chat.id ? '#ffffff' : 'var(--color-text-muted)' }} />
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium text-sm truncate" style={{ color: 'var(--color-text-primary)' }}>
                                                    {chat.name || 'New Conversation'}
                                                </p>
                                                <p className="text-xs truncate mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                                                    {chat.messages?.length || 0} messages
                                                </p>
                                            </div>

                                            {currentChatId === chat.id && (
                                                <div className="w-2 h-2 rounded-full" style={{ background: '#10B981' }} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer Actions */}
                        <div className="p-4 flex items-center justify-between" style={{ borderTop: '1px solid var(--color-border)' }}>
                            <button
                                onClick={() => {
                                    clearChat()
                                    setShowMobileHistory(false)
                                }}
                                disabled={chatHistory.filter(c => c.messages?.length > 0).length === 0}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-50"
                                style={{ color: '#F87171', background: 'rgba(248, 113, 113, 0.1)' }}
                            >
                                <Trash2 className="w-4 h-4" />
                                Clear All
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
