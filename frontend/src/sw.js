/**
 * FAiND Service Worker — Section 29 (Feature U).
 * - Precache static assets (cache-first via workbox precaching)
 * - Cache-first for runtime static assets
 * - Network-only for API; offline fallback for navigations
 * - Web Push handlers (Section 11.3)
 */
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { registerRoute, setCatchHandler } from 'workbox-routing'
import { CacheFirst, NetworkFirst } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// Section 29.2 — cache-first for static assets (never API routes)
registerRoute(
  ({ request, url }) => {
    if (url.pathname.startsWith('/api')) return false
    return ['style', 'script', 'image', 'font', 'manifest'].includes(request.destination)
  },
  new CacheFirst({
    cacheName: 'faind-static-runtime',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 120,
        maxAgeSeconds: 30 * 24 * 60 * 60,
      }),
    ],
  }),
)

const navigationHandler = new NetworkFirst({
  cacheName: 'faind-navigation',
  networkTimeoutSeconds: 5,
  plugins: [
    {
      handlerDidError: async () => {
        const offline = await caches.match('/offline.html')
        if (offline) return offline
        const shell = createHandlerBoundToURL('/index.html')
        return shell({ request: new Request('/index.html') })
      },
    },
  ],
})

registerRoute(({ request }) => request.mode === 'navigate', navigationHandler)

setCatchHandler(async ({ event }) => {
  if (event.request.mode === 'navigate') {
    const offline = await caches.match('/offline.html')
    if (offline) return offline
  }
  return Response.error()
})

// ─── Push notification handler (Section 11.3) ────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: 'FAiND', body: event.data ? event.data.text() : 'You have a new notification.' }
  }

  const title = data.title || 'FAiND'
  const options = {
    body: data.body || 'You have a new notification.',
    icon: data.icon || '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    data: { url: data.url || '/' },
    vibrate: [200, 100, 200],
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = (event.notification.data && event.notification.data.url) || '/'

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl)
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl)
      }
    }),
  )
})
