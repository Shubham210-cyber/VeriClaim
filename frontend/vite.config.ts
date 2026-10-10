import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The browser only talks to this dev server; /api is proxied to the local backend.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' } },
})
