import { useNavigate } from 'react-router-dom'
import {
    ArrowLeft, Shield, Database, Lock, Eye, Trash2, Mail,
    Clock, Server, FileText, AlertTriangle, CheckCircle
} from 'lucide-react'

export default function Privacy() {
    const navigate = useNavigate()

    const sections = [
        {
            icon: Database,
            title: "1. Data We Collect",
            content: [
                {
                    subtitle: "Account Data",
                    items: [
                        "Email address (used for authentication)",
                        "Name (optional, used for personalisation)",
                        "Password (securely hashed with bcrypt — never stored in plain text)"
                    ]
                },
                {
                    subtitle: "Nutritional Profile Data",
                    items: [
                        "Age, weight, height, and biological sex",
                        "Nutritional goals (e.g., weight loss, muscle gain, maintenance)",
                        "Physical activity level",
                        "Dietary restrictions, allergies, and diet type",
                        "Food preferences"
                    ]
                },
                {
                    subtitle: "Interaction Data",
                    items: [
                        "Conversation history with the AI assistant",
                        "Generated meal plans and nutritional calculations"
                    ]
                }
            ]
        },
        {
            icon: Lock,
            title: "2. How We Protect Your Data",
            content: [
                {
                    subtitle: "Security Measures",
                    items: [
                        "Passwords hashed with bcrypt (never stored in plain text)",
                        "JWT tokens for authenticated sessions",
                        "HTTPS encryption for all communications",
                        "PostgreSQL database with restricted access controls",
                        "Data is not shared with any third parties"
                    ]
                }
            ]
        },
        {
            icon: Eye,
            title: "3. Purpose of Data Processing",
            content: [
                {
                    subtitle: "Your data is used to:",
                    items: [
                        "Calculate personalised nutritional metrics (BMR, TDEE, macronutrients)",
                        "Generate evidence-based dietary recommendations",
                        "Create meal plans tailored to your profile and goals",
                        "Maintain conversation history for context continuity",
                        "Improve the overall application experience"
                    ]
                },
                {
                    subtitle: "Your data is NOT used for:",
                    items: [
                        "Targeted advertising",
                        "Sale or transfer to third parties",
                        "Commercial profiling",
                        "Marketing without explicit consent"
                    ],
                    warning: true
                }
            ]
        },
        {
            icon: Server,
            title: "4. Local Storage",
            content: [
                {
                    subtitle: "NourishGraph stores the following data locally in your browser:",
                    items: [
                        "Authentication token (session management)",
                        "Theme preference (light or dark mode)",
                        "Onboarding completion status",
                        "Cookie consent preferences"
                    ]
                },
                {
                    subtitle: "Important:",
                    items: [
                        "No tracking cookies are used",
                        "No third-party analytics services (e.g., Google Analytics) are integrated",
                        "You can clear all locally stored data at any time through your browser settings"
                    ]
                }
            ]
        },
        {
            icon: Clock,
            title: "5. Data Retention",
            content: [
                {
                    subtitle: "Your data is retained:",
                    items: [
                        "For as long as your account remains active",
                        "Until you explicitly request deletion",
                        "Accounts inactive for more than 2 years may be automatically deleted in future versions"
                    ]
                }
            ]
        },
        {
            icon: FileText,
            title: "6. Your Rights (GDPR)",
            content: [
                {
                    subtitle: "Under the General Data Protection Regulation, you have the right to:",
                    items: [
                        "Access: Request a copy of all data we hold about you",
                        "Rectification: Correct any inaccurate data in your profile",
                        "Erasure: Delete your account and all associated data",
                        "Portability: Export your data in a portable format (planned feature)",
                        "Objection: Refuse non-essential data processing"
                    ]
                },
                {
                    subtitle: "How to exercise your rights:",
                    items: [
                        "Go to Settings → Delete Account to permanently erase all your data",
                        "Edit your profile directly to correct any information",
                        "Contact us via email for any other data-related requests"
                    ]
                }
            ]
        }
    ]

    return (
        <div className="min-h-screen p-4 sm:p-6 animate-fadeIn" style={{ background: 'var(--color-bg-primary)' }}>
            <div className="max-w-3xl mx-auto">
                {/* Header */}
                <div className="flex items-center gap-4 mb-8">
                    <button
                        onClick={() => navigate(-1)}
                        className="p-2.5 rounded-xl transition-all hover:-translate-x-1"
                        style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}
                    >
                        <ArrowLeft className="w-5 h-5" style={{ color: 'var(--color-text-muted)' }} />
                    </button>
                    <div>
                        <div className="flex items-center gap-3">
                            <div
                                className="w-10 h-10 rounded-xl flex items-center justify-center"
                                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}
                            >
                                <Shield className="w-5 h-5 text-white" />
                            </div>
                            <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
                                Privacy Policy
                            </h1>
                        </div>
                        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
                            Last updated: February 2026
                        </p>
                    </div>
                </div>

                {/* Introduction */}
                <div
                    className="rounded-xl p-5 mb-6"
                    style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}
                >
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                        <strong>NourishGraph</strong> was developed as part of a Master's thesis at
                        <strong> NOVA Information Management School (NOVA IMS)</strong>, Universidade NOVA de Lisboa.
                        Your privacy is important to us. This policy describes what data we collect,
                        how it is used, how it is protected, and your rights under the
                        <strong> General Data Protection Regulation (GDPR)</strong>.
                    </p>
                </div>

                {/* Sections */}
                <div className="space-y-6">
                    {sections.map((section, idx) => (
                        <div
                            key={idx}
                            className="rounded-xl overflow-hidden"
                            style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}
                        >
                            <div
                                className="px-5 py-4 flex items-center gap-3"
                                style={{ borderBottom: '1px solid var(--color-border)' }}
                            >
                                <div
                                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                                    style={{ background: 'rgba(16, 185, 129, 0.1)' }}
                                >
                                    <section.icon className="w-4 h-4" style={{ color: 'var(--color-primary)' }} />
                                </div>
                                <h2 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                                    {section.title}
                                </h2>
                            </div>
                            <div className="p-5 space-y-4">
                                {section.content.map((block, blockIdx) => (
                                    <div key={blockIdx}>
                                        <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>
                                            {block.subtitle}
                                        </p>
                                        <ul className="space-y-1.5">
                                            {block.items.map((item, itemIdx) => (
                                                <li
                                                    key={itemIdx}
                                                    className="flex items-start gap-2 text-sm"
                                                    style={{ color: 'var(--color-text-secondary)' }}
                                                >
                                                    {block.warning ? (
                                                        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                                                    ) : (
                                                        <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                                                    )}
                                                    {item}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Contact */}
                <div
                    className="rounded-xl p-5 mt-6"
                    style={{ background: 'var(--color-bg-card)', border: '1px solid var(--color-border)' }}
                >
                    <div className="flex items-center gap-3 mb-3">
                        <Mail className="w-5 h-5" style={{ color: 'var(--color-primary)' }} />
                        <h3 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                            Contact
                        </h3>
                    </div>
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        For privacy-related questions or to exercise any of your data rights, please contact:
                    </p>
                    <a
                        href="mailto:20240349@novaims.unl.pt"
                        className="inline-flex items-center gap-2 text-sm mt-2 font-medium hover:underline transition-colors"
                        style={{ color: 'var(--color-primary)' }}
                    >
                        Bárbara Peres - NOVA IMS
                    </a>
                    <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                        20240349@novaims.unl.pt
                    </p>
                </div>

                {/* Academic Note */}
                <div
                    className="rounded-xl p-5 mt-6"
                    style={{
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid rgba(59, 130, 246, 0.3)'
                    }}
                >
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        <strong>Academic Note:</strong> This project was developed as part of a Master's thesis
                        at NOVA Information Management School (NOVA IMS). All data is processed exclusively
                        for academic research and system demonstration purposes, and is not used for any
                        commercial activity.
                    </p>
                </div>

                {/* Footer */}
                <div className="text-center py-8">
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        © 2026 NourishGraph - Master's Thesis Project, NOVA IMS
                    </p>
                </div>
            </div>
        </div>
    )
}
