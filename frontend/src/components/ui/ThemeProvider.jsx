/**
 * NourishGraph Theme Provider
 * Sistema de temas com suporte a light/dark mode
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';

// Theme types
const THEMES = {
    LIGHT: 'light',
    DARK: 'dark',
    SYSTEM: 'system',
};

// Context
const ThemeContext = createContext(null);

// Get system preference
const getSystemTheme = () => {
    if (typeof window !== 'undefined') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
};

// Theme Provider Component
export const ThemeProvider = ({ children, defaultTheme = 'system', storageKey = 'nourishgraph-theme' }) => {
    const [theme, setThemeState] = useState(() => {
        if (typeof window !== 'undefined') {
            const stored = localStorage.getItem(storageKey);
            return stored || defaultTheme;
        }
        return defaultTheme;
    });

    const [resolvedTheme, setResolvedTheme] = useState(() => {
        return theme === 'system' ? getSystemTheme() : theme;
    });

    // Apply theme to document
    useEffect(() => {
        const root = window.document.documentElement;
        const resolved = theme === 'system' ? getSystemTheme() : theme;

        root.classList.remove('light', 'dark');
        root.classList.add(resolved);
        root.setAttribute('data-theme', resolved);

        setResolvedTheme(resolved);
    }, [theme]);

    // Listen for system theme changes
    useEffect(() => {
        if (theme !== 'system') return;

        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

        const handleChange = (e) => {
            const newTheme = e.matches ? 'dark' : 'light';
            const root = window.document.documentElement;
            root.classList.remove('light', 'dark');
            root.classList.add(newTheme);
            root.setAttribute('data-theme', newTheme);
            setResolvedTheme(newTheme);
        };

        mediaQuery.addEventListener('change', handleChange);
        return () => mediaQuery.removeEventListener('change', handleChange);
    }, [theme]);

    // Set theme function
    const setTheme = (newTheme) => {
        localStorage.setItem(storageKey, newTheme);
        setThemeState(newTheme);
    };

    // Toggle between light and dark (ignoring system)
    const toggleTheme = () => {
        const newTheme = resolvedTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    };

    const value = {
        theme,
        resolvedTheme,
        setTheme,
        toggleTheme,
        isDark: resolvedTheme === 'dark',
        isLight: resolvedTheme === 'light',
        themes: THEMES,
    };

    return (
        <ThemeContext.Provider value={value}>
            {children}
        </ThemeContext.Provider>
    );
};

// Hook
export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
};

// Theme Toggle Button Component
export const ThemeToggle = ({
    showLabel = false,
    size = 'md',
    className = ''
}) => {
    const { resolvedTheme, toggleTheme, isDark } = useTheme();

    const sizes = {
        sm: 'w-8 h-8',
        md: 'w-10 h-10',
        lg: 'w-12 h-12',
    };

    const iconSizes = {
        sm: 'w-4 h-4',
        md: 'w-5 h-5',
        lg: 'w-6 h-6',
    };

    return (
        <button
            onClick={toggleTheme}
            className={`
        ${sizes[size]} rounded-xl
        flex items-center justify-center gap-2
        transition-all duration-200
        ${className}
      `}
            style={{
                background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                border: 'none',
                color: '#ffffff'
            }}
            title={isDark ? 'Mudar para modo claro' : 'Mudar para modo escuro'}
            aria-label={isDark ? 'Mudar para modo claro' : 'Mudar para modo escuro'}
        >
            {isDark ? (
                <Sun className={iconSizes[size]} style={{ color: '#ffffff', stroke: '#ffffff', fill: 'none' }} />
            ) : (
                <Moon className={iconSizes[size]} style={{ color: '#ffffff', stroke: '#ffffff', fill: 'none' }} />
            )}
            {showLabel && (
                <span className="text-sm" style={{ color: '#ffffff' }}>
                    {isDark ? 'Claro' : 'Escuro'}
                </span>
            )}
        </button>
    );
};

// Theme Selector Component (3 options)
export const ThemeSelector = ({ className = '' }) => {
    const { theme, setTheme } = useTheme();

    const options = [
        { value: 'light', icon: Sun, label: 'Claro' },
        { value: 'dark', icon: Moon, label: 'Escuro' },
        { value: 'system', icon: Monitor, label: 'Sistema' },
    ];

    return (
        <div className={`inline-flex rounded-lg bg-hover p-1 ${className}`}>
            {options.map((option) => {
                const IconComponent = option.icon;
                const isActive = theme === option.value;

                return (
                    <button
                        key={option.value}
                        onClick={() => setTheme(option.value)}
                        className={`
              flex items-center gap-2 px-3 py-1.5 rounded-md text-sm
              transition-all duration-200
              ${isActive
                                ? 'bg-card text-text-primary shadow-sm'
                                : 'text-text-muted hover:text-text-secondary'
                            }
            `}
                        title={option.label}
                    >
                        <IconComponent className="w-4 h-4" />
                        <span className="hidden sm:inline">{option.label}</span>
                    </button>
                );
            })}
        </div>
    );
};

export default { ThemeProvider, useTheme, ThemeToggle, ThemeSelector };
