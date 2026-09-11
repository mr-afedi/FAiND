/**
 * usePushNotifications — manages Web Push permission + subscription lifecycle.
 *
 * Permission timing (Section 11.3): NEVER request on login.
 * The hook exposes:
 *   - promptReady: true once the user has a notification-worthy event and
 *     hasn't yet granted/denied permission.
 *   - requestPermissionAndSubscribe(): shows native dialog then subscribes.
 *   - unsubscribe(): unsubscribe from push.
 *   - permissionState: 'default' | 'granted' | 'denied'
 *   - isSubscribed: boolean
 */
import { useState, useEffect, useCallback } from 'react'
import { subscribeToPush, unsubscribeFromPush, getCurrentPushSubscription } from '../services/pushService'

const PUSH_SUPPORTED =
  typeof window !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window

export function usePushNotifications() {
  const [permissionState, setPermissionState] = useState(
    PUSH_SUPPORTED ? Notification.permission : 'unsupported'
  )
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Check current subscription on mount
  useEffect(() => {
    if (!PUSH_SUPPORTED) return
    getCurrentPushSubscription().then((sub) => setIsSubscribed(!!sub))
  }, [])

  const requestPermissionAndSubscribe = useCallback(async () => {
    if (!PUSH_SUPPORTED) return false
    setLoading(true)
    setError(null)
    try {
      const permission = await Notification.requestPermission()
      setPermissionState(permission)
      if (permission !== 'granted') {
        setLoading(false)
        return false
      }
      await subscribeToPush()
      setIsSubscribed(true)
      setLoading(false)
      return true
    } catch (err) {
      setError(err.message || 'Failed to subscribe.')
      setLoading(false)
      return false
    }
  }, [])

  const unsubscribe = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await unsubscribeFromPush()
      setIsSubscribed(false)
    } catch (err) {
      setError(err.message || 'Failed to unsubscribe.')
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    supported: PUSH_SUPPORTED,
    permissionState,
    isSubscribed,
    loading,
    error,
    requestPermissionAndSubscribe,
    unsubscribe,
  }
}
