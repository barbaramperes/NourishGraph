import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App'
import { ThemeProvider } from './components/ui/ThemeProvider'
import { ToastProvider } from './components/ui/Toast'
import './styles/design-system.css'
import './index.css'

// Google OAuth Client ID (public, not secret)
const GOOGLE_CLIENT_ID = '73751302632-186hikb6g6ceamhpo232vhe590gc3op3.apps.googleusercontent.com'

// Error Boundary for debugging
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, errorInfo) {
        console.error('React Error:', error, errorInfo)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '40px', fontFamily: 'system-ui', background: '#1a1a2e', color: '#fff', minHeight: '100vh' }}>
                    <h1 style={{ color: '#ef4444' }}>Something went wrong</h1>
                    <pre style={{ background: '#0f0f1a', padding: '20px', borderRadius: '8px', overflow: 'auto', color: '#fbbf24' }}>
                        {this.state.error?.toString()}
                    </pre>
                    <button
                        onClick={() => window.location.reload()}
                        style={{ marginTop: '20px', padding: '10px 20px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                    >
                        Reload Page
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}

const AppProviders = ({ children }) => (
    <ErrorBoundary>
        <ThemeProvider defaultTheme="system">
            <ToastProvider>
                {children}
            </ToastProvider>
        </ThemeProvider>
    </ErrorBoundary>
)

ReactDOM.createRoot(document.getElementById('root')).render(
    GOOGLE_CLIENT_ID ? (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <AppProviders>
                <App />
            </AppProviders>
        </GoogleOAuthProvider>
    ) : (
        <AppProviders>
            <App />
        </AppProviders>
    )
)
