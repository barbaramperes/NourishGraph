import { useEffect, useRef, useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { useTheme } from './ui/ThemeProvider'

// Google Identity Services renders its button at a fixed pixel width in this range.
const MIN_WIDTH = 200
const MAX_WIDTH = 400

/**
 * "Sign in with Google" button rendered by Google Identity Services.
 *
 * On success it hands back the Google ID token (a signed JWT "credential"),
 * which the backend verifies server-side at POST /auth/google.
 */
export default function GoogleSignInButton({ onCredential, onError, disabled = false, text = 'continue_with' }) {
    const { isDark } = useTheme()
    const containerRef = useRef(null)
    const [width, setWidth] = useState(320)

    // Match the container width so the button lines up with the form fields.
    useEffect(() => {
        const el = containerRef.current
        if (!el) return undefined
        const update = () => {
            const w = Math.round(el.getBoundingClientRect().width)
            if (w > 0) setWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, w)))
        }
        update()
        if (typeof ResizeObserver === 'undefined') return undefined
        const observer = new ResizeObserver(update)
        observer.observe(el)
        return () => observer.disconnect()
    }, [])

    return (
        <div
            ref={containerRef}
            aria-disabled={disabled}
            className={`w-full flex justify-center transition-opacity ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        >
            <GoogleLogin
                onSuccess={(response) => {
                    if (response?.credential) {
                        onCredential(response.credential)
                    } else {
                        onError?.()
                    }
                }}
                onError={() => onError?.()}
                text={text}
                theme={isDark ? 'filled_black' : 'outline'}
                shape="rectangular"
                size="large"
                width={width}
            />
        </div>
    )
}
