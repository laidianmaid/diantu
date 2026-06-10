import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [vue(), basicSsl()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE || 'http://backend:8000',
        changeOrigin: true,
      },
      '/_AMapService': {
        target: process.env.VITE_API_BASE || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
