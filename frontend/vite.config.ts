
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
  },
  // Disable inline source maps to avoid Node.js native heap assertion crashes.
  css: {
    devSourcemap: false,
  },
  build: {
    sourcemap: false,
    // Split Mapbox into its own chunk.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/mapbox-gl')) {
            return 'mapbox'
          }
        },
      },
    },
  },
  // Prevent Mapbox from being pre-bundled during development.
  optimizeDeps: {
    exclude: ['mapbox-gl'],
  },
})
