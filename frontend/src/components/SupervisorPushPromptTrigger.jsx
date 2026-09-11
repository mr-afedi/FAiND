import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { supervisorApi } from '../services/supervisorService'
import { markStaffPushPromptReady } from '../utils/staffPushPrompt'

async function getSupervisorAlerts() {
  const { data } = await supervisorApi.get('/supervisor/alerts')
  return data
}

export default function SupervisorPushPromptTrigger() {
  const seenIdsRef = useRef(new Set())

  const { data } = useQuery({
    queryKey: ['supervisor-alerts-push-trigger'],
    queryFn: getSupervisorAlerts,
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
    if (armed) markStaffPushPromptReady('supervisor')
  }, [data])

  return null
}
