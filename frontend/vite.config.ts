import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // El .env compartido vive en la raíz del monorepo; solo se exponen las variables VITE_*.
  envDir: '..',
})
