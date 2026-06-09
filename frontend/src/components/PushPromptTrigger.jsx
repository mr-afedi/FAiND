/**
 * Watches for notification-worthy events and arms the contextual push prompt.
 * Section 11.3 — never requests permission on login.
 */
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { getMyNotifications } from '../services/matchService'
import { markPushPromptReady, NOTIFICATION_WORTHY_TYPES } from '../utils/pushPrompt'

export default function PushPromptTrigger() {
  const { isAuthenticated } = useAuth()
  const seenIdsRef = useRef(new Set())

  const { data } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: getMyNotifications,
    enabled: isAuthenticated,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  useEffect(() => {
    if (!isAuthenticated || !data?.notifications?.length) return

    let armed = false
    for (const notif of data.notifications) {
      if (!NOTIFICATION_WORTHY_TYPES.has(notif.notification_type)) continue
      if (seenIdsRef.current.has(notif.id)) continue
      seenIdsRef.current.add(notif.id)
      armed = true
    }
    if (armed) markPushPromptReady()
  }, [data, isAuthenticated])

  return null
}
