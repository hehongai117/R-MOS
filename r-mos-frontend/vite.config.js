import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import sirv from 'sirv';
var serveRobotAssets = function () { return ({
    name: 'serve-robot-assets',
    configureServer: function (server) {
        var repoRoot = path.resolve(__dirname, '..');
        var robotDir = path.join(repoRoot, 'robot');
        server.middlewares.use('/robot', sirv(robotDir, {
            dev: true,
            etag: true,
        }));
    },
}); };
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
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://127.0.0.1:8000',
                ws: true,
            },
        },
    },
    build: {
        chunkSizeWarningLimit: 3000,
    },
});
