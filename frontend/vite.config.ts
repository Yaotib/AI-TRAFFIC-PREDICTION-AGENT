import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
  },
  // Disable inline source maps — prevents a Node.js native heap assertion
  // crash (genSourceMapUrl) that occurs on some Node versions with large maps.
  css: {
    devSourcemap: false,
  },
  build: {
    sourcemap: false,
    // Split mapbox-gl into its own chunk so it isn't inlined into main bundle
    rollupOptions: {
      output: {
        manualChunks: {
          mapbox: ['mapbox-gl'],
        },
      },
    },
  },
  // Prevent esbuild/Rollup from pre-bundling mapbox-gl (it's huge and causes OOM)
  optimizeDeps: {
    exclude: ['mapbox-gl'],
  },
})

