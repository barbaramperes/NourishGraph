/**
 * Advanced Markdown Renderer for NourishGraph
 * 
 * Renders AI responses with beautiful formatting:
 * - Headers with icons
 * - Numbered lists with badges
 * - Bullet points with teal accents
 * - Tables with nutrition styling
 * - Code blocks with syntax highlighting
 * - Bold/italic text
 * - Blockquotes for important info
 */
import { memo } from 'react'
import {
    Lightbulb, AlertCircle, CheckCircle2, Info,
    Utensils, FlaskConical, Heart, Zap, Target,
    ArrowRight, Sparkles
} from 'lucide-react'

// Parse markdown to structured elements
function parseMarkdown(text) {
    if (!text) return []

    const lines = text.split('\n')
    const elements = []
    let currentList = null
    let currentListType = null
    let tableRows = []
    let inTable = false
    let tableHeaders = []

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const trimmed = line.trim()

        // Skip empty lines but close lists
        if (!trimmed) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
                currentListType = null
            }
            if (inTable && tableRows.length > 0) {
                elements.push({ type: 'table', headers: tableHeaders, rows: tableRows })
                tableRows = []
                tableHeaders = []
                inTable = false
            }
            continue
        }

        // Table detection
        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
            const cells = trimmed.slice(1, -1).split('|').map(c => c.trim())

            // Skip separator row
            if (cells.every(c => /^[-:]+$/.test(c))) {
                continue
            }

            if (!inTable) {
                inTable = true
                tableHeaders = cells
            } else {
                tableRows.push(cells)
            }
            continue
        } else if (inTable) {
            elements.push({ type: 'table', headers: tableHeaders, rows: tableRows })
            tableRows = []
            tableHeaders = []
            inTable = false
        }

        // Headers
        if (trimmed.startsWith('#### ')) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
            }
            elements.push({ type: 'h4', content: trimmed.slice(5) })
            continue
        }
        if (trimmed.startsWith('### ')) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
            }
            elements.push({ type: 'h3', content: trimmed.slice(4) })
            continue
        }
        if (trimmed.startsWith('## ')) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
            }
            elements.push({ type: 'h2', content: trimmed.slice(3) })
            continue
        }
        if (trimmed.startsWith('# ')) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
            }
            elements.push({ type: 'h1', content: trimmed.slice(2) })
            continue
        }

        // Blockquotes
        if (trimmed.startsWith('> ')) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
            }
            elements.push({ type: 'blockquote', content: trimmed.slice(2) })
            continue
        }

        // Paper reference with bold number (e.g., **1. Author et al. (2021)**)
        const paperRefMatch = trimmed.match(/^\*\*(\d+)\.\s+(.+?)\*\*\s*[-–—]?\s*(.*)$/)
        if (paperRefMatch) {
            if (currentList) {
                elements.push({ type: currentListType, items: currentList })
                currentList = null
                currentListType = null
            }
            elements.push({ 
                type: 'paperRef', 
                number: parseInt(paperRefMatch[1]), 
                author: paperRefMatch[2],
                title: paperRefMatch[3] || ''
            })
            continue
        }

        // Numbered lists
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/)
        if (numberedMatch) {
            if (currentListType !== 'numbered') {
                if (currentList) {
                    elements.push({ type: currentListType, items: currentList })
                }
                currentList = []
                currentListType = 'numbered'
            }
            currentList.push({ number: parseInt(numberedMatch[1]), content: numberedMatch[2] })
            continue
        }

        // Bullet lists
        if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
            if (currentListType !== 'bullet') {
                if (currentList) {
                    elements.push({ type: currentListType, items: currentList })
                }
                currentList = []
                currentListType = 'bullet'
            }
            currentList.push({ content: trimmed.slice(2) })
            continue
        }

        // Regular paragraph
        if (currentList) {
            elements.push({ type: currentListType, items: currentList })
            currentList = null
            currentListType = null
        }
        elements.push({ type: 'paragraph', content: trimmed })
    }

    // Close any open list
    if (currentList) {
        elements.push({ type: currentListType, items: currentList })
    }
    if (inTable && tableRows.length > 0) {
        elements.push({ type: 'table', headers: tableHeaders, rows: tableRows })
    }

    return elements
}

// Format inline markdown (bold, italic, links)
function formatInline(text) {
    if (!text) return text

    // Bold
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-[var(--color-text-primary)]">$1</strong>')

    // Italic
    text = text.replace(/\*([^*]+)\*/g, '<em class="italic text-[var(--color-text-secondary)]">$1</em>')

    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-[var(--color-bg-elevated)] text-[#10B981] font-mono text-xs">$1</code>')

    // Links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="text-[#10B981] hover:text-[#34D399] underline underline-offset-2 transition-colors">$1</a>')

    return text
}

// Get icon for header based on content
function getHeaderIcon(content) {
    const lower = content.toLowerCase()
    if (lower.includes('benefit') || lower.includes('advantage')) return <CheckCircle2 className="w-4 h-4" />
    if (lower.includes('warning') || lower.includes('caution') || lower.includes('risk')) return <AlertCircle className="w-4 h-4" />
    if (lower.includes('tip') || lower.includes('recommendation')) return <Lightbulb className="w-4 h-4" />
    if (lower.includes('food') || lower.includes('meal') || lower.includes('eat')) return <Utensils className="w-4 h-4" />
    if (lower.includes('science') || lower.includes('study') || lower.includes('research')) return <FlaskConical className="w-4 h-4" />
    if (lower.includes('health') || lower.includes('heart')) return <Heart className="w-4 h-4" />
    if (lower.includes('energy') || lower.includes('calorie')) return <Zap className="w-4 h-4" />
    if (lower.includes('goal') || lower.includes('target')) return <Target className="w-4 h-4" />
    return <Sparkles className="w-4 h-4" />
}

// Render a single element
function renderElement(element, index) {
    switch (element.type) {
        case 'h1':
            return (
                <h2 key={index} className="flex items-center gap-2 text-lg font-bold mt-4 mb-3 pb-2 border-b border-[var(--color-border)]" style={{ color: 'var(--color-text-primary)' }}>
                    <span className="w-7 h-7 rounded-lg flex items-center justify-center text-white" style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}>
                        {getHeaderIcon(element.content)}
                    </span>
                    <span dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
                </h2>
            )

        case 'h2':
            return (
                <h3 key={index} className="flex items-center gap-2 text-base font-bold mt-4 mb-2" style={{ color: 'var(--color-text-primary)' }}>
                    <span className="w-1.5 h-5 rounded-full" style={{ background: 'linear-gradient(180deg, #10B981 0%, #059669 100%)' }} />
                    <span dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
                </h3>
            )

        case 'h3':
            return (
                <h4 key={index} className="flex items-center gap-2 text-sm font-semibold mt-3 mb-1.5" style={{ color: '#10B981' }}>
                    <ArrowRight className="w-3.5 h-3.5" />
                    <span dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
                </h4>
            )

        case 'h4':
            return (
                <h5 key={index} className="flex items-center gap-2 text-sm font-medium mt-2.5 mb-1" style={{ color: '#14B8A6' }}>
                    <span className="w-1 h-1 rounded-full bg-[#14B8A6]" />
                    <span dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
                </h5>
            )

        case 'paperRef':
            return (
                <div key={index} className="mt-4 mb-2">
                    <div className="flex items-start gap-3">
                        <span className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 text-white shadow-md"
                            style={{ 
                                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                                boxShadow: '0 2px 8px rgba(16, 185, 129, 0.35)'
                            }}>
                            {element.number}
                        </span>
                        <div className="flex-1">
                            <span className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                                {element.author}
                            </span>
                            {element.title && (
                                <span className="text-sm font-semibold italic ml-1" style={{ color: 'var(--color-text-secondary)' }}>
                                    {element.title}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            )

        case 'blockquote':
            return (
                <div key={index} className="my-3 pl-4 py-2 border-l-3 rounded-r-lg" style={{ borderColor: '#10B981', background: 'rgba(16, 185, 129, 0.1)' }}>
                    <div className="flex items-start gap-2">
                        <Info className="w-4 h-4 mt-0.5 shrink-0" style={{ color: '#10B981' }} />
                        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
                    </div>
                </div>
            )

        case 'numbered':
            return (
                <div key={index} className="my-3 space-y-2">
                    {element.items.map((item, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-xl transition-colors hover:bg-[var(--color-bg-elevated)]" style={{ background: 'var(--color-bg-secondary)' }}>
                            <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 text-white" style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}>
                                {item.number}
                            </span>
                            <span className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(item.content) }} />
                        </div>
                    ))}
                </div>
            )

        case 'bullet':
            return (
                <div key={index} className="my-2 space-y-1.5 pl-1">
                    {element.items.map((item, i) => (
                        <div key={i} className="flex items-start gap-2.5">
                            <span className="w-1.5 h-1.5 rounded-full mt-2 shrink-0" style={{ background: '#10B981' }} />
                            <span className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(item.content) }} />
                        </div>
                    ))}
                </div>
            )

        case 'table':
            return (
                <div key={index} className="my-4 overflow-x-auto rounded-xl" style={{ border: '1px solid var(--color-border)' }}>
                    <table className="w-full text-sm">
                        <thead>
                            <tr style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)' }}>
                                {element.headers.map((header, i) => (
                                    <th key={i} className="px-4 py-2.5 text-left font-semibold" style={{ color: 'var(--color-text-primary)', borderBottom: '1px solid var(--color-border)' }}>
                                        {header}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {element.rows.map((row, i) => (
                                <tr key={i} className="transition-colors hover:bg-[var(--color-bg-elevated)]" style={{ borderBottom: i < element.rows.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                                    {row.map((cell, j) => (
                                        <td key={j} className="px-4 py-2.5" style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(cell) }} />
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )

        case 'paragraph':
        default:
            return (
                <p key={index} className="my-2 text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }} dangerouslySetInnerHTML={{ __html: formatInline(element.content) }} />
            )
    }
}

// Main component
function MarkdownRenderer({ content }) {
    if (!content) return null

    const elements = parseMarkdown(content)

    return (
        <div className="markdown-content">
            {elements.map((element, index) => renderElement(element, index))}
        </div>
    )
}

export default memo(MarkdownRenderer)
