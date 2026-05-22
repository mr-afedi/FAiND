/**
 * FAiND Service Worker — handles push events + workbox precaching.
 * vite-plugin-pwa (injectManifest strategy) injects self.__WB_MANIFEST below.
 */
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

// Injected by vite-plugin-pwa at build time
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

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

// ─── Notification click → deep-link into app ─────────────────────────────────
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
    })
  )
})
