import { useState, useEffect, useCallback } from 'react'
import {
  subscribeStaffPush,
  unsubscribeStaffPush,
  getCurrentStaffPushSubscription,
} from '../services/staffPushService'

const PUSH_SUPPORTED =
  typeof window !== 'undefined' &&
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window

export function useStaffPushNotifications(role) {
  const [permissionState, setPermissionState] = useState(
    PUSH_SUPPORTED ? Notification.permission : 'unsupported'
  )
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!PUSH_SUPPORTED) return
    getCurrentStaffPushSubscription().then((sub) => setIsSubscribed(!!sub))
  }, [])

  const requestPermissionAndSubscribe = useCallback(async () => {
    if (!PUSH_SUPPORTED || !role) return false
    setLoading(true)
    setError(null)
    try {
      const permission = await Notification.requestPermission()
      setPermissionState(permission)
      if (permission !== 'granted') {
        setLoading(false)
        return false
      }
      await subscribeStaffPush(role)
      setIsSubscribed(true)
      setLoading(false)
      return true
    } catch (err) {
      setError(err.message || 'Failed to subscribe')
      setLoading(false)
      return false
    }
  }, [role])

  const unsubscribe = useCallback(async () => {
    if (!PUSH_SUPPORTED || !role) return
    setLoading(true)
    try {
      await unsubscribeStaffPush(role)
      setIsSubscribed(false)
    } finally {
      setLoading(false)
    }
  }, [role])

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
