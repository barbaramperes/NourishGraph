/** @type {import('tailwindcss').Config} */
export default {
    darkMode: 'class',
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Primary - Emerald/Teal (Harmonious)
                primary: {
                    DEFAULT: '#10B981',
                    50: 'rgba(16, 185, 129, 0.08)',
                    100: 'rgba(16, 185, 129, 0.12)',
                    200: '#A7F3D0',
                    300: '#6EE7B7',
                    400: '#34D399',
                    500: '#10B981',
                    600: '#059669',
                    700: '#047857',
                    800: '#065F46',
                    900: '#064E3B',
                },
                // Secondary - Cyan
                secondary: {
                    DEFAULT: '#06B6D4',
                    50: 'rgba(6, 182, 212, 0.08)',
                    100: 'rgba(6, 182, 212, 0.12)',
                    300: '#67E8F9',
                    400: '#22D3EE',
                    500: '#06B6D4',
                    600: '#0891B2',
                    700: '#0E7490',
                },
                // Backgrounds
                background: '#0A0A0B',
                surface: '#141416',
                card: '#1C1C1F',
                hover: '#252529',
                border: '#2E2E32',
                // Text
                text: {
                    DEFAULT: '#FAFAFA',
                    primary: '#FAFAFA',
                    secondary: '#A1A1AA',
                    muted: '#71717A',
                },
                // Semantic
                error: '#EF4444',
                success: '#10B981',
                warning: '#F59E0B',
                info: '#06B6D4',
            },
            fontFamily: {
                display: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
                body: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
                'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
                'hero-gradient': 'linear-gradient(135deg, #00D9A5 0%, #0EA5E9 100%)',
                'card-gradient': 'linear-gradient(145deg, rgba(39, 39, 42, 0.4) 0%, rgba(24, 24, 27, 0.6) 100%)',
            },
            boxShadow: {
                'glow': '0 0 60px rgba(0, 217, 165, 0.15)',
                'glow-sm': '0 0 30px rgba(0, 217, 165, 0.1)',
                'glow-lg': '0 0 80px rgba(0, 217, 165, 0.2)',
                'card': '0 20px 40px -12px rgba(0, 0, 0, 0.4)',
                'button': '0 8px 30px rgba(0, 217, 165, 0.3)',
            },
            animation: {
                'fadeIn': 'fadeIn 0.4s ease-out',
                'fadeInUp': 'fadeInUp 0.5s ease-out',
                'fadeInDown': 'fadeInDown 0.5s ease-out',
                'slideInRight': 'slideInRight 0.4s ease-out',
                'slideUp': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
                'slideDown': 'slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                'scaleIn': 'scaleIn 0.3s ease-out',
                'float': 'float 6s ease-in-out infinite',
                'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
                'shimmer': 'shimmer 2s infinite',
                'spin-slow': 'spin 3s linear infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                fadeInUp: {
                    '0%': { opacity: '0', transform: 'translateY(20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                fadeInDown: {
                    '0%': { opacity: '0', transform: 'translateY(-20px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(20px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(30px) scale(0.96)' },
                    '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
                },
                slideDown: {
                    '0%': { opacity: '0', transform: 'translateY(-10px) scale(0.96)' },
                    '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
                },
                scaleIn: {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
                    '50%': { transform: 'translateY(-20px) rotate(2deg)' },
                },
                'pulse-glow': {
                    '0%, 100%': { boxShadow: '0 0 20px rgba(0, 217, 165, 0.3)' },
                    '50%': { boxShadow: '0 0 40px rgba(0, 217, 165, 0.5)' },
                },
                shimmer: {
                    '0%': { backgroundPosition: '-200% 0' },
                    '100%': { backgroundPosition: '200% 0' },
                },
            },
            borderRadius: {
                '4xl': '2rem',
            },
        },
    },
    plugins: [],
}
