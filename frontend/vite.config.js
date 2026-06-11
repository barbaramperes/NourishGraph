import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use backend service name in Docker, localhost outside
const API_TARGET = process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
            '/chat': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/profile': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/meals': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/auth': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/health': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/stats': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/foods': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/history': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/papers': {
                target: API_TARGET,
                changeOrigin: true
            },
            '/api': {
                target: API_TARGET,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            }
        }
    }
})
