import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'http://localhost:8001')
  },
  server: {
    port: 3001,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend:8001',
        changeOrigin: true,
      }
    }
  }
})
