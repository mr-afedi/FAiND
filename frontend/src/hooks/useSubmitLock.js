import { useCallback, useRef, useState } from 'react'

/**
 * Synchronous submit guard — disables UI immediately on first click,
 * before React Query's isPending flips (prevents double-submit).
 */
export function useSubmitLock() {
  const lockedRef = useRef(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const tryAcquire = useCallback(() => {
    if (lockedRef.current) return false
    lockedRef.current = true
    setIsSubmitting(true)
    return true
  }, [])

  const release = useCallback(() => {
    lockedRef.current = false
    setIsSubmitting(false)
  }, [])

  return { isSubmitting, tryAcquire, release }
}
