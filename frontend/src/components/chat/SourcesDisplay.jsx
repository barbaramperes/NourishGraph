/**
 * SourcesDisplay - Professional scientific citations component
 * 
 * Displays scientific papers cited by the AI with:
 * - Title, Authors, Year, Journal
 * - Expandable details with abstract preview
 * - Visual indicators for evidence strength
 * - Hover tooltips with more details
 * - "Evidence-Based" badge indicator
 */

import { useState, useRef } from 'react'
import {
    ChevronDown,
    ChevronUp,
    FileText,
    ExternalLink,
    BookOpen,
    GraduationCap,
    Calendar,
    Users,
    CheckCircle2,
    Sparkles,
    Info,
    Copy,
    Check
} from 'lucide-react'

// Evidence level badge colors and labels
const evidenceLevels = {
    A: { label: 'Strong Evidence', color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)', description: 'Multiple high-quality studies support this information' },
    B: { label: 'Moderate Evidence', color: '#3B82F6', bg: 'rgba(59, 130, 246, 0.12)', description: 'Good quality research supports this information' },
    C: { label: 'Limited Evidence', color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', description: 'Some research supports this, but more studies needed' },
    D: { label: 'Preliminary', color: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.12)', description: 'Early research, findings may change with more data' },
}

/**
 * Tooltip component for hover details
 */
const Tooltip = ({ children, content, position = 'top' }) => {
    const [show, setShow] = useState(false)
    const [coords, setCoords] = useState({ top: 0, left: 0 })
    const triggerRef = useRef(null)

    const handleMouseEnter = () => {
        if (triggerRef.current) {
            const rect = triggerRef.current.getBoundingClientRect()
            setCoords({
                top: position === 'top' ? rect.top - 8 : rect.bottom + 8,
                left: rect.left + rect.width / 2
            })
        }
        setShow(true)
    }

    return (
        <div
            ref={triggerRef}
            className="relative inline-flex"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={() => setShow(false)}
        >
            {children}
            {show && (
                <div
                    className="fixed z-[9999] px-3 py-2 text-xs rounded-lg shadow-xl max-w-xs pointer-events-none animate-fadeIn"
                    style={{
                        top: position === 'top' ? coords.top : coords.top,
                        left: coords.left,
                        transform: `translate(-50%, ${position === 'top' ? '-100%' : '0'})`,
                        background: 'var(--color-bg-elevated)',
                        border: '1px solid var(--color-border)',
                        color: 'var(--color-text-primary)'
                    }}
                >
                    {content}
                </div>
            )}
        </div>
    )
}

/**
 * Evidence-Based Badge - Shows that response is backed by science
 */
export const EvidenceBadge = ({ sourceCount, evidenceLevel = 'B', className = '' }) => {
    const evidence = evidenceLevels[evidenceLevel] || evidenceLevels.B

    return (
        <Tooltip
            content={
                <div className="space-y-1">
                    <div className="font-semibold" style={{ color: evidence.color }}>{evidence.label}</div>
                    <div style={{ color: 'var(--color-text-secondary)' }}>{evidence.description}</div>
                    <div className="text-[10px] mt-1" style={{ color: 'var(--color-text-muted)' }}>
                        Based on {sourceCount} scientific source{sourceCount > 1 ? 's' : ''}
                    </div>
                </div>
            }
        >
            <div
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all hover:scale-105 cursor-help ${className}`}
                style={{
                    background: evidence.bg,
                    color: evidence.color,
                    border: `1px solid ${evidence.color}30`
                }}
            >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Evidence-Based</span>
                {sourceCount > 0 && (
                    <span
                        className="ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-bold"
                        style={{ background: evidence.color, color: 'white' }}
                    >
                        {sourceCount}
                    </span>
                )}
            </div>
        </Tooltip>
    )
}

/**
 * Single source card component with hover tooltip
 */
const SourceCard = ({ source, index, isExpanded, onToggle }) => {
    const [copied, setCopied] = useState(false)

    // Extract data from source (handle different formats)
    const title = source.title || source.paper || 'Scientific Paper'
    const authors = source.authors || source.author || null
    const year = source.year || source.date?.slice(0, 4) || null
    const journal = source.journal || source.source || null
    const abstract = source.abstract || source.snippet || source.text || null
    const doi = source.doi || null
    const url = source.url || (doi ? `https://doi.org/${doi}` : null)
    const score = source.score || source.relevance || null

    // Format authors nicely
    const formatAuthors = (auth) => {
        if (!auth) return null
        if (Array.isArray(auth)) {
            if (auth.length > 3) {
                return `${auth.slice(0, 3).join(', ')} et al.`
            }
            return auth.join(', ')
        }
        return auth
    }

    // Copy citation
    const copyCitation = (e) => {
        e.stopPropagation()
        const citation = `${formatAuthors(authors) || 'Unknown'} (${year || 'n.d.'}). ${title}. ${journal || ''}`
        navigator.clipboard.writeText(citation)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div
            className="group rounded-xl overflow-hidden transition-all duration-300"
            style={{
                background: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
                boxShadow: isExpanded ? '0 8px 24px rgba(16, 185, 129, 0.1)' : '0 2px 8px rgba(0,0,0,0.05)'
            }}
        >
            {/* Header - Always visible */}
            <button
                onClick={onToggle}
                className="w-full p-4 flex items-start gap-3 text-left transition-colors hover:bg-black/5 dark:hover:bg-white/5"
            >
                {/* Index badge */}
                <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 font-semibold text-sm"
                    style={{
                        background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                        color: 'white',
                        boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)'
                    }}
                >
                    {index + 1}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    {/* Title */}
                    <h4
                        className="font-medium text-sm leading-snug mb-1.5 line-clamp-2 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors"
                        style={{ color: 'var(--color-text-primary)' }}
                    >
                        {title}
                    </h4>

                    {/* Meta info row */}
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {authors && (
                            <Tooltip content={Array.isArray(authors) ? authors.join(', ') : authors}>
                                <span className="flex items-center gap-1 cursor-help">
                                    <Users className="w-3 h-3" />
                                    <span className="truncate max-w-[180px]">{formatAuthors(authors)}</span>
                                </span>
                            </Tooltip>
                        )}
                        {year && (
                            <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {year}
                            </span>
                        )}
                        {journal && (
                            <Tooltip content={journal}>
                                <span className="flex items-center gap-1 cursor-help">
                                    <BookOpen className="w-3 h-3" />
                                    <span className="truncate max-w-[120px]">{journal}</span>
                                </span>
                            </Tooltip>
                        )}
                        {score && (
                            <Tooltip content={`Relevance score: ${(score * 100).toFixed(0)}%`}>
                                <span
                                    className="flex items-center gap-1 px-1.5 py-0.5 rounded cursor-help"
                                    style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981' }}
                                >
                                    <Sparkles className="w-3 h-3" />
                                    {(score * 100).toFixed(0)}%
                                </span>
                            </Tooltip>
                        )}
                    </div>
                </div>

                {/* Expand icon */}
                <div
                    className="p-1.5 rounded-lg transition-colors"
                    style={{ background: isExpanded ? 'rgba(16, 185, 129, 0.1)' : 'transparent' }}
                >
                    {isExpanded ? (
                        <ChevronUp className="w-4 h-4" style={{ color: '#10B981' }} />
                    ) : (
                        <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-text-muted)' }} />
                    )}
                </div>
            </button>

            {/* Expanded content */}
            {isExpanded && (
                <div
                    className="px-4 pb-4 pt-0 border-t animate-fadeIn"
                    style={{ borderColor: 'var(--color-border)' }}
                >
                    {/* Abstract/Snippet */}
                    {abstract && (
                        <div className="mt-3 p-3 rounded-lg" style={{ background: 'var(--color-bg-secondary)' }}>
                            <div className="flex items-center gap-1.5 mb-2 text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                                <FileText className="w-3 h-3" />
                                Abstract Preview
                            </div>
                            <p
                                className="text-xs leading-relaxed"
                                style={{ color: 'var(--color-text-secondary)' }}
                            >
                                {abstract.length > 350 ? abstract.slice(0, 350) + '...' : abstract}
                            </p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                        {url && (
                            <a
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:scale-105"
                                style={{
                                    background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                    color: 'white',
                                    boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)'
                                }}
                            >
                                <ExternalLink className="w-3 h-3" />
                                View Full Paper
                            </a>
                        )}
                        <button
                            onClick={copyCitation}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:scale-105"
                            style={{
                                background: 'var(--color-bg-secondary)',
                                color: 'var(--color-text-secondary)',
                                border: '1px solid var(--color-border)'
                            }}
                        >
                            {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                            {copied ? 'Copied!' : 'Copy Citation'}
                        </button>
                        {doi && (
                            <span
                                className="text-[10px] px-2 py-1.5 rounded-lg font-mono"
                                style={{
                                    background: 'var(--color-bg-secondary)',
                                    color: 'var(--color-text-muted)',
                                    border: '1px solid var(--color-border)'
                                }}
                            >
                                DOI: {doi}
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

/**
 * Main SourcesDisplay component - Expandable/collapsible source list
 */
export const SourcesDisplay = ({ sources, evidenceLevel, className = '' }) => {
    const [isExpanded, setIsExpanded] = useState(false)
    const [expandedCards, setExpandedCards] = useState({})

    // Filter sources that have meaningful data
    const validSources = (sources || []).filter(s => s.title?.trim() || s.paper?.trim())

    if (validSources.length === 0) return null

    const toggleCard = (index) => {
        setExpandedCards(prev => ({
            ...prev,
            [index]: !prev[index]
        }))
    }

    const evidence = evidenceLevels[evidenceLevel] || evidenceLevels.B

    return (
        <div className={`mt-4 ${className}`}>
            {/* Header bar - Clickable to expand/collapse */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-3 rounded-xl transition-all hover:shadow-md"
                style={{
                    background: evidence.bg,
                    border: `1px solid ${evidence.color}25`
                }}
            >
                <div className="flex items-center gap-3">
                    {/* Icon with glow */}
                    <div className="relative">
                        <div
                            className="absolute inset-0 rounded-lg blur-md opacity-50"
                            style={{ background: evidence.color }}
                        />
                        <div
                            className="relative w-9 h-9 rounded-lg flex items-center justify-center"
                            style={{
                                background: `linear-gradient(135deg, ${evidence.color} 0%, ${evidence.color}dd 100%)`,
                                boxShadow: `0 4px 12px ${evidence.color}40`
                            }}
                        >
                            <GraduationCap className="w-5 h-5 text-white" />
                        </div>
                    </div>

                    {/* Label */}
                    <div className="text-left">
                        <div className="flex items-center gap-2">
                            <span
                                className="text-sm font-semibold"
                                style={{ color: evidence.color }}
                            >
                                {validSources.length} Scientific Source{validSources.length > 1 ? 's' : ''}
                            </span>
                            <Tooltip content={evidence.description}>
                                <span
                                    className="text-[10px] font-bold px-2 py-0.5 rounded-full cursor-help"
                                    style={{
                                        background: evidence.color,
                                        color: 'white'
                                    }}
                                >
                                    {evidence.label}
                                </span>
                            </Tooltip>
                        </div>
                        <span
                            className="text-xs"
                            style={{ color: 'var(--color-text-muted)' }}
                        >
                            {isExpanded ? 'Click to collapse' : 'Click to view cited papers'}
                        </span>
                    </div>
                </div>

                {/* Expand indicator */}
                <div
                    className="p-2 rounded-lg transition-transform duration-300"
                    style={{
                        background: `${evidence.color}15`,
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'
                    }}
                >
                    <ChevronDown className="w-4 h-4" style={{ color: evidence.color }} />
                </div>
            </button>

            {/* Expandable sources list */}
            {isExpanded && (
                <div className="mt-3 space-y-2 animate-slideUp">
                    {validSources.map((source, index) => (
                        <SourceCard
                            key={source.title || index}
                            source={source}
                            index={index}
                            isExpanded={expandedCards[index] || false}
                            onToggle={() => toggleCard(index)}
                        />
                    ))}

                    {/* Footer disclaimer */}
                    <div
                        className="flex items-start gap-2 p-3 rounded-lg text-xs"
                        style={{
                            background: 'var(--color-bg-secondary)',
                            color: 'var(--color-text-muted)'
                        }}
                    >
                        <Info className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>
                            Sources are retrieved using RAG (Retrieval-Augmented Generation) from our scientific paper database.
                            Always verify important information with the original publications.
                        </span>
                    </div>
                </div>
            )}
        </div>
    )
}

/**
 * Compact inline citations - ChatGPT/Claude style
 * Simple clickable numbered badges that open the sources panel
 */
export const InlineCitations = ({ sources, onSourceClick, className = '' }) => {
    const validSources = (sources || []).filter(s => s.title?.trim() || s.paper?.trim())

    if (validSources.length === 0) return null

    return (
        <div className={`flex flex-wrap items-center gap-1 mt-3 ${className}`}>
            <span className="text-xs mr-1" style={{ color: 'var(--color-text-muted)' }}>
                Sources:
            </span>
            {validSources.map((source, i) => {
                const title = source.title || source.paper || 'Source'

                return (
                    <Tooltip
                        key={i}
                        content={
                            <div className="max-w-xs">
                                <div className="font-medium text-xs">{title}</div>
                            </div>
                        }
                    >
                        <button
                            onClick={() => onSourceClick?.(i)}
                            className="inline-flex items-center justify-center w-5 h-5 rounded text-[11px] font-semibold cursor-pointer transition-all hover:scale-110 hover:shadow-md"
                            style={{
                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                color: 'white',
                                boxShadow: '0 1px 3px rgba(16, 185, 129, 0.3)'
                            }}
                        >
                            {i + 1}
                        </button>
                    </Tooltip>
                )
            })}
        </div>
    )
}

/**
 * Legacy inline sources for backwards compatibility
 */
export const InlineSources = ({ sources, className = '' }) => {
    return <InlineCitations sources={sources} className={className} />
}

export default SourcesDisplay
