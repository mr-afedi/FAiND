/**
 * In-app offline indicator — Section 29.2.
 * Static shell may load from cache; dynamic data shows this banner.
 */
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { WifiOff } from './icons'

export default function OfflineBanner() {
  const online = useOnlineStatus()
  if (online) return null

  return (
    <div
      className="fixed top-0 inset-x-0 z-[60] flex items-center justify-center gap-2
                 bg-amber-500 text-white text-xs font-medium py-2 px-4 shadow-md"
      role="status"
      aria-live="polite"
    >
      <WifiOff className="w-4 h-4 shrink-0" aria-hidden />
      You are offline — items, matches, and messages need a live connection.
    </div>
  )
}
