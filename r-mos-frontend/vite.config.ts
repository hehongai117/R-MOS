import { defineConfig, type Plugin, type ViteDevServer } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import sirv from 'sirv'

const serveRobotAssets = (): Plugin => ({
  name: 'serve-robot-assets',
  configureServer(server: ViteDevServer) {
    const repoRoot = path.resolve(__dirname, '..')
    const robotDir = path.join(repoRoot, 'robot')

    server.middlewares.use(
      '/robot',
      sirv(robotDir, {
        dev: true,
        etag: true,
      })
    )
  },
})

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), serveRobotAssets()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
