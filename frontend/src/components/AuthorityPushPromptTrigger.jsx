import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAuthorityAlerts } from '../services/authorityService'
import { markStaffPushPromptReady } from '../utils/staffPushPrompt'

export default function AuthorityPushPromptTrigger() {
  const seenIdsRef = useRef(new Set())

  const { data } = useQuery({
    queryKey: ['authority-alerts-push-trigger'],
    queryFn: getAuthorityAlerts,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  useEffect(() => {
    if (!data?.alerts?.length) return
    let armed = false
    for (const alert of data.alerts) {
      if (seenIdsRef.current.has(alert.id)) continue
      seenIdsRef.current.add(alert.id)
      armed = true
    }
    if (armed) markStaffPushPromptReady('authority')
  }, [data])

  return null
}
