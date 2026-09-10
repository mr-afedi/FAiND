/**
 * staffPushService.js — Web Push for authority, supervisor, and admin accounts.
 */
import api from './api'
import authorityApi from './authorityService'
import { supervisorApi } from './supervisorService'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = atob(base64)
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)))
}

async function getVapidPublicKey() {
  const envKey = import.meta.env.VITE_VAPID_PUBLIC_KEY
  if (envKey && envKey !== 'your-vapid-public-key') return envKey
  const res = await api.get('/push/vapid-public-key')
  return res.data.public_key
}

async function swReady(timeoutMs = 8000) {
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Service worker not ready')), timeoutMs)
    ),
  ])
}

async function subscribeWithApi(client, subscribePath, unsubscribePath) {
  const registration = await swReady()
  const vapidPublicKey = await getVapidPublicKey()
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  })
  const json = subscription.toJSON()
  await client.post(subscribePath, {
    endpoint: json.endpoint,
    p256dh: json.keys.p256dh,
    auth: json.keys.auth,
  })
  return subscription
}

async function unsubscribeWithApi(client, unsubscribePath) {
  const registration = await swReady()
  const subscription = await registration.pushManager.getSubscription()
  if (!subscription) return
  const endpoint = subscription.endpoint
  await subscription.unsubscribe()
  try {
    await client.delete(unsubscribePath, { data: { endpoint } })
  } catch {
    // best effort
  }
}

const STAFF_CONFIG = {
  authority: {
    client: authorityApi,
    subscribePath: '/authority/push/subscribe',
    unsubscribePath: '/authority/push/subscribe',
    settingsPath: '/authority/push-settings',
  },
  supervisor: {
    client: supervisorApi,
    subscribePath: '/supervisor/push/subscribe',
    unsubscribePath: '/supervisor/push/subscribe',
    settingsPath: '/supervisor/push-settings',
  },
  admin: {
    client: api,
    subscribePath: '/push/admin/subscribe',
    unsubscribePath: '/push/admin/subscribe',
    settingsPath: '/push/admin/settings',
  },
}

export async function subscribeStaffPush(role) {
  const cfg = STAFF_CONFIG[role]
  if (!cfg) throw new Error(`Unknown staff role: ${role}`)
  return subscribeWithApi(cfg.client, cfg.subscribePath, cfg.unsubscribePath)
}

export async function unsubscribeStaffPush(role) {
  const cfg = STAFF_CONFIG[role]
  if (!cfg) return
  return unsubscribeWithApi(cfg.client, cfg.unsubscribePath)
}

export async function getStaffPushSettings(role) {
  const cfg = STAFF_CONFIG[role]
  const { data } = await cfg.client.get(cfg.settingsPath)
  return data
}

export async function updateStaffPushSettings(role, push_notifications_enabled) {
  const cfg = STAFF_CONFIG[role]
  const { data } = await cfg.client.patch(cfg.settingsPath, { push_notifications_enabled })
  return data
}

export async function getCurrentStaffPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null
  try {
    const registration = await swReady(3000)
    return registration.pushManager.getSubscription()
  } catch {
    return null
  }
}
