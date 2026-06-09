import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.js',
      registerType: 'autoUpdate',
      includeAssets: [
        'favicon.ico',
        'apple-touch-icon.png',
        'masked-icon.svg',
        'offline.html',
        'pwa-192x192.png',
        'pwa-512x512.png',
      ],
      manifest: {
        name: 'FAiND',
        short_name: 'FAiND',
        description: 'AI-powered lost and found platform for university campuses',
        theme_color: '#3b82f6',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
      // Register the service worker in dev mode so push subscriptions work
      // during development (not just in production builds).
      devOptions: {
        enabled: true,
        type: 'module',
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('react-dom') || id.includes('/react/')) {
            return 'react-vendor'
          }
          if (id.includes('react-router') || id.includes('@remix-run/router')) {
            return 'react-router'
          }
          if (id.includes('@tanstack/react-query')) {
            return 'tanstack-query'
          }
          if (id.includes('/axios/')) {
            return 'axios'
          }
          if (id.includes('lucide-react')) {
            return 'lucide-react'
          }
          if (id.includes('react-hot-toast') || id.includes('/goober/')) {
            return 'react-hot-toast'
          }
          return undefined
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
