import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Em desenvolvimento (npm run dev) as chamadas a /api vão para o FastAPI local.
// Em produção o próprio FastAPI serve este build, então /api é o mesmo domínio.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
