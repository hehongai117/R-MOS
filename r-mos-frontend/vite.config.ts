import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 3000,
        proxy: {
            // 代理 /api/v1 到后端服务
            '/api/v1': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            // 代理 WebSocket
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
            },
        },
    },
})
