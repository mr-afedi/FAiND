import api from './api'

/**
 * Convert a VAPID public key string (base64url) to a Uint8Array
 * as required by pushManager.subscribe().
 */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

export async function getVapidPublicKey() {
  // Prefer env var to avoid an extra round-trip
  const envKey = import.meta.env.VITE_VAPID_PUBLIC_KEY
  if (envKey && envKey !== 'your-vapid-public-key') return envKey
  const res = await api.get('/push/vapid-public-key')
  return res.data.public_key
}

async function _swReady(timeoutMs = 8000) {
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error('Service worker did not become ready in time. Try reloading the page.')),
        timeoutMs
      )
    ),
  ])
}

export async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Web Push is not supported in this browser.')
  }

  const registration = await _swReady()
  const vapidPublicKey = await getVapidPublicKey()
  const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey)

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  })

  const json = subscription.toJSON()
  await api.post('/push/subscribe', {
    endpoint: json.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  })

  return subscription
}

export async function unsubscribeFromPush() {
  if (!('serviceWorker' in navigator)) return
  try {
    const registration = await _swReady()
    const subscription = await registration.pushManager.getSubscription()
    if (!subscription) return

    const endpoint = subscription.endpoint
    await subscription.unsubscribe()

    try {
      await api.delete('/push/subscribe', { data: { endpoint } })
    } catch {
      // Best-effort cleanup — ignore if subscription was already removed on server
    }
  } catch {
    // SW not ready — nothing to unsubscribe
  }
}

export async function getCurrentPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null
  try {
    const registration = await _swReady(3000)
    return registration.pushManager.getSubscription()
  } catch {
    return null
  }
}
