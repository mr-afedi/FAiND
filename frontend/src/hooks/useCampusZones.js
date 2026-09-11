/**
 * Campus zones for report forms — stable while the user is filling the form.
 * Global React Query defaults use staleTime: 0; this query opts out so
 * refetches do not swap the location dropdown for a loading placeholder.
 */
import { useMemo } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { getCampusZones } from '../services/itemService'

export function useCampusZones() {
  const query = useQuery({
    queryKey: ['campus-zones'],
    queryFn: getCampusZones,
    staleTime: 1000 * 60 * 10,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  })

  const zones = useMemo(
    () => (Array.isArray(query.data) ? query.data : []),
    [query.data],
  )

  const zonesLoading = query.isPending && zones.length === 0

  return { zones, zonesLoading, ...query }
}

function generateQuestionId() {
  // randomUUID requires a secure context (HTTPS/localhost). LAN HTTP on phones is not secure.
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      return crypto.randomUUID()
    } catch {
      /* insecure context — use fallback */
    }
  }
  return `q-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

function newQuestion() {
  return { id: generateQuestionId(), question: '', answer: '' }
}

export function createInitialQuestions(count = 2) {
  return Array.from({ length: count }, () => newQuestion())
}

export { newQuestion }
