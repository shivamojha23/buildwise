import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  // Load .env so we can reference VITE_API_BASE_URL at config time.
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      // Proxy /api and /health to the FastAPI backend during local development.
      // This avoids CORS issues when running both servers simultaneously.
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true,
        },
        '/health': {
          target: apiBaseUrl,
          changeOrigin: true,
        },
      },
    },
  }
})
