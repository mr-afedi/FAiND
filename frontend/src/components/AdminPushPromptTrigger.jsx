import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import { markStaffPushPromptReady } from '../utils/staffPushPrompt'

async function getAdminNotifications() {
  const { data } = await api.get('/notifications')
  return data
}

export default function AdminPushPromptTrigger() {
  const seenIdsRef = useRef(new Set())

  const { data } = useQuery({
    queryKey: ['admin-notifications-push-trigger'],
    queryFn: getAdminNotifications,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  useEffect(() => {
    if (!data?.notifications?.length) return
    let armed = false
    for (const notif of data.notifications) {
      if (seenIdsRef.current.has(notif.id)) continue
      seenIdsRef.current.add(notif.id)
      armed = true
    }
    if (armed) markStaffPushPromptReady('admin')
  }, [data])

  return null
}
