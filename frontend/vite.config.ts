import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The browser only talks to this dev server; /api is proxied to the local backend.
// VITE_API_TARGET lets a second instance point at a different backend port.
const api = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': api, '/health': api } },
})
