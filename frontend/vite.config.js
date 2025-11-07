import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Allow local override via env: VITE_API_TARGET or APP_PORT
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || `http://localhost:${env.APP_PORT || '9187'}`

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true
        }
      }
    },
    build: {
      outDir: '../api-gateway/static',
      emptyOutDir: false,
      assetsDir: 'assets',
      rollupOptions: {
        output: {
          manualChunks: undefined
        }
      }
    }
  }
})
