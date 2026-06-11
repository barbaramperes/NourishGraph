import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactPlugin from 'eslint-plugin-react'

export default [
    js.configs.recommended,
    {
        files: ['**/*.{js,jsx}'],
        languageOptions: {
            ecmaVersion: 2024,
            sourceType: 'module',
            globals: {
                window: 'readonly',
                document: 'readonly',
                localStorage: 'readonly',
                sessionStorage: 'readonly',
                navigator: 'readonly',
                fetch: 'readonly',
                console: 'readonly',
                setTimeout: 'readonly',
                clearTimeout: 'readonly',
                setInterval: 'readonly',
                clearInterval: 'readonly',
                alert: 'readonly',
                confirm: 'readonly',
                process: 'readonly',
                EventSource: 'readonly',
                AbortController: 'readonly',
                TextDecoder: 'readonly',
                URL: 'readonly',
                URLSearchParams: 'readonly',
                FormData: 'readonly',
                Blob: 'readonly',
                File: 'readonly',
                FileReader: 'readonly',
                Image: 'readonly',
                Audio: 'readonly',
                speechSynthesis: 'readonly',
                SpeechSynthesisUtterance: 'readonly',
                MediaRecorder: 'readonly',
                AudioContext: 'readonly',
                webkitAudioContext: 'readonly',
                location: 'readonly',
                history: 'readonly',
                IntersectionObserver: 'readonly',
                ResizeObserver: 'readonly',
                MutationObserver: 'readonly',
                requestAnimationFrame: 'readonly',
                cancelAnimationFrame: 'readonly',
            },
            parserOptions: {
                ecmaFeatures: {
                    jsx: true,
                },
            },
        },
        plugins: {
            react: reactPlugin,
            'react-hooks': reactHooks,
        },
        rules: {
            // React rules
            'react/jsx-uses-react': 'error',
            'react/jsx-uses-vars': 'error',
            'react/prop-types': 'off', // We're not using prop-types
            'react/react-in-jsx-scope': 'off', // Not needed in React 17+

            // React Hooks rules
            'react-hooks/rules-of-hooks': 'error',
            'react-hooks/exhaustive-deps': 'warn',

            // General rules
            'no-unused-vars': ['warn', {
                argsIgnorePattern: '^_',
                varsIgnorePattern: '^_'
            }],
            'no-console': 'off', // Allow console for debugging
            'no-debugger': 'warn',
            'prefer-const': 'warn',
            'no-var': 'error',
            'eqeqeq': ['warn', 'always', { null: 'ignore' }],
        },
        settings: {
            react: {
                version: 'detect',
            },
        },
    },
    {
        ignores: ['node_modules/**', 'dist/**', 'build/**'],
    },
]
