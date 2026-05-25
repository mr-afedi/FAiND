/**
 * PushPromptBanner — contextual push-permission prompt (Section 11.3).
 *
 * Shown after a match-found notification arrives (or any notification-worthy
 * event) when the user has not yet granted/denied push permission.
 *
 * Usage:
 *   <PushPromptBanner />
 *
 * The banner stores dismissal in localStorage so it does not nag the user
 * on every render.
 */
import { useState } from 'react'
import { usePushNotifications } from '../hooks/usePushNotifications'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { Bell } from './icons'

const DISMISSED_KEY = 'faind:push_prompt_dismissed'

export default function PushPromptBanner() {
  const { isAuthenticated } = useAuth()
  const { supported, permissionState, isSubscribed, loading, requestPermissionAndSubscribe } =
    usePushNotifications()

  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === 'true'
  )

  // Only show when:
  //  - User is logged in (never shown to guests — spec §11.3)
  //  - Push is supported in this browser
  //  - Permission not yet decided
  //  - Not already subscribed
  //  - User hasn't dismissed this banner
  if (!isAuthenticated || !supported || permissionState !== 'default' || isSubscribed || dismissed) return null

  const handleAccept = async () => {
    const ok = await requestPermissionAndSubscribe()
    if (ok) {
        toast.success('Push notifications enabled! You will be alerted for matches and messages.')
    } else {
      toast('You can enable push notifications later in Settings.', { icon: <Bell className="w-5 h-5" /> })
    }
    setDismissed(true)
    localStorage.setItem(DISMISSED_KEY, 'true')
  }

  const handleDismiss = () => {
    setDismissed(true)
    localStorage.setItem(DISMISSED_KEY, 'true')
  }

  return (
    <div className="fixed bottom-20 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
      <div className="pointer-events-auto w-full max-w-sm bg-white dark:bg-gray-800 border border-blue-200 dark:border-blue-700 rounded-2xl shadow-2xl p-4 flex gap-3 items-start">
        <Bell className="w-6 h-6 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            Turn on push notifications?
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Get alerts for matches and messages on your phone or desktop — even when the app is closed.
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleAccept}
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-lg transition-colors disabled:opacity-60"
            >
              {loading ? 'Enabling…' : 'Enable'}
            </button>
            <button
              onClick={handleDismiss}
              className="flex-1 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 text-xs font-semibold py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Not now
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
