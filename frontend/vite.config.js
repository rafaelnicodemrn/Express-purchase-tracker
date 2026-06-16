import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/pedidos': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
    },
  },
})
