/**
 * NourishGraph Toast Notifications
 * Enhanced toast notification system with animations and progress bar
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { CheckCircle, AlertCircle, AlertTriangle, Info, X, Sparkles, Zap } from 'lucide-react';

// Context
const ToastContext = createContext(null);

// Toast types configuration with gradients
const TOAST_CONFIG = {
    success: {
        icon: CheckCircle,
        gradient: 'linear-gradient(135deg, #10B981, #059669)',
        bgGradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))',
        borderColor: '#10B981',
        textColor: '#10B981',
    },
    error: {
        icon: AlertCircle,
        gradient: 'linear-gradient(135deg, #EF4444, #DC2626)',
        bgGradient: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.08))',
        borderColor: '#EF4444',
        textColor: '#EF4444',
    },
    warning: {
        icon: AlertTriangle,
        gradient: 'linear-gradient(135deg, #F59E0B, #D97706)',
        bgGradient: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.08))',
        borderColor: '#F59E0B',
        textColor: '#F59E0B',
    },
    info: {
        icon: Info,
        gradient: 'linear-gradient(135deg, #10B981, #059669)',
        bgGradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))',
        borderColor: '#10B981',
        textColor: '#10B981',
    },
    proactive: {
        icon: Sparkles,
        gradient: 'linear-gradient(135deg, #10B981, #059669)',
        bgGradient: 'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))',
        borderColor: '#10B981',
        textColor: '#10B981',
    },
    ai: {
        icon: Zap,
        gradient: 'linear-gradient(135deg, #8B5CF6, #7C3AED)',
        bgGradient: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(124, 58, 237, 0.08))',
        borderColor: '#8B5CF6',
        textColor: '#8B5CF6',
    },
};

// Single Toast Component with progress bar
const Toast = ({ id, type = 'info', title, message, onClose, duration = 5000 }) => {
    const config = TOAST_CONFIG[type] || TOAST_CONFIG.info;
    const IconComponent = config.icon;
    const [progress, setProgress] = useState(100);
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        if (duration > 0) {
            const startTime = Date.now();
            const interval = setInterval(() => {
                const elapsed = Date.now() - startTime;
                const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
                setProgress(remaining);

                if (remaining <= 0) {
                    clearInterval(interval);
                    handleClose();
                }
            }, 50);
            return () => clearInterval(interval);
        }
    }, [duration]);

    const handleClose = () => {
        setIsExiting(true);
        setTimeout(() => onClose(id), 200);
    };

    return (
        <div
            className={`relative flex items-start gap-3 p-4 rounded-xl shadow-2xl max-w-sm w-full overflow-hidden transition-all duration-200 ${isExiting ? 'opacity-0 translate-x-4 scale-95' : 'opacity-100 translate-x-0 scale-100'
                }`}
            style={{
                background: 'var(--color-bg-elevated)',
                border: `1px solid ${config.borderColor}30`,
                boxShadow: `0 10px 40px rgba(0,0,0,0.3), 0 0 20px ${config.borderColor}15`,
            }}
            role="alert"
        >
            {/* Left border accent */}
            <div
                className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl"
                style={{ background: config.gradient }}
            />

            {/* Icon with gradient background */}
            <div
                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center shadow-lg"
                style={{ background: config.gradient }}
            >
                <IconComponent className="w-5 h-5" style={{ color: '#ffffff' }} strokeWidth={2.5} />
            </div>

            <div className="flex-1 min-w-0 ml-1">
                {title && (
                    <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>{title}</p>
                )}
                {message && (
                    <p className="text-sm mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{message}</p>
                )}
            </div>

            <button
                onClick={handleClose}
                className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors"
                style={{ color: 'var(--color-text-muted)' }}
            >
                <X className="w-4 h-4" />
            </button>

            {/* Progress bar */}
            {duration > 0 && (
                <div
                    className="absolute bottom-0 left-0 h-0.5 transition-all duration-100 ease-linear rounded-full"
                    style={{
                        width: `${progress}%`,
                        background: config.gradient,
                        opacity: 0.8
                    }}
                />
            )}
        </div>
    );
};

// Toast Container - Bottom right with animation
const ToastContainer = ({ toasts, removeToast }) => {
    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col-reverse gap-3 pointer-events-none">
            {toasts.map((toast, index) => (
                <div
                    key={toast.id}
                    className="pointer-events-auto"
                    style={{
                        animation: `slideInRight 0.3s ease-out ${index * 0.05}s both`
                    }}
                >
                    <Toast
                        {...toast}
                        onClose={removeToast}
                    />
                </div>
            ))}
        </div>
    );
};

// Toast Provider
export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((toast) => {
        const id = Date.now().toString();
        setToasts((prev) => [...prev, { id, ...toast }]);
        return id;
    }, []);

    const removeToast = useCallback((id) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);

    const toast = {
        success: (message, title) => addToast({ type: 'success', message, title }),
        error: (message, title) => addToast({ type: 'error', message, title }),
        warning: (message, title) => addToast({ type: 'warning', message, title }),
        info: (message, title) => addToast({ type: 'info', message, title }),
        proactive: (message, title) => addToast({ type: 'proactive', message, title, duration: 8000 }),
        ai: (message, title) => addToast({ type: 'ai', message, title, duration: 6000 }),
        custom: (options) => addToast(options),
        dismiss: removeToast,
        dismissAll: () => setToasts([]),
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}
            <ToastContainer toasts={toasts} removeToast={removeToast} />
        </ToastContext.Provider>
    );
};

// Hook
export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

export default { ToastProvider, useToast };
