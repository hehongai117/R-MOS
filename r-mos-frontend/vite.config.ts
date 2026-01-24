import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import sirv from 'sirv'

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
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },

    // 本机开发：把仓库根目录的 robot/ 暴露成静态资源
    // 访问路径示例： http://localhost:3000/robot/roboto_origin/...
    configureServer(server) {
      const repoRoot = path.resolve(__dirname, '..')
      const robotDir = path.join(repoRoot, 'robot')

      server.middlewares.use(
        '/robot',
        sirv(robotDir, {
          dev: true,
          etag: true,
        })
      )

      // 如果你还想把根目录其它大资源也映射，可按同样方式追加
      // server.middlewares.use('/assets', sirv(path.join(repoRoot, 'assets'), { dev: true }))
    },
  },
})
