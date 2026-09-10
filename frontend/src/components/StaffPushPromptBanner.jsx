/**
 * StaffPushPromptBanner — contextual push prompt for authority/supervisor/admin.
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Bell } from './icons'
import { useStaffPushNotifications } from '../hooks/useStaffPushNotifications'
import {
  dismissStaffPushPrompt,
  isStaffPushPromptDismissed,
  isStaffPushPromptReady,
  STAFF_PUSH_PROMPT_READY_EVENT,
} from '../utils/staffPushPrompt'

export default function StaffPushPromptBanner({ role, enabled }) {
  const { supported, permissionState, isSubscribed, loading, requestPermissionAndSubscribe } =
    useStaffPushNotifications(role)

  const [promptReady, setPromptReady] = useState(() => isStaffPushPromptReady(role))
  const [dismissed, setDismissed] = useState(() => isStaffPushPromptDismissed(role))

  useEffect(() => {
    const eventName = STAFF_PUSH_PROMPT_READY_EVENT(role)
    const onReady = () => setPromptReady(true)
    window.addEventListener(eventName, onReady)
    return () => window.removeEventListener(eventName, onReady)
  }, [role])

  if (
    !enabled ||
    !supported ||
    !promptReady ||
    permissionState !== 'default' ||
    isSubscribed ||
    dismissed
  ) {
    return null
  }

  const handleAccept = async () => {
    const ok = await requestPermissionAndSubscribe()
    if (ok) {
      toast.success('Push notifications enabled for your staff account.')
    } else {
      toast('You can enable push notifications later in Settings.', { icon: <Bell className="w-5 h-5" /> })
    }
    dismissStaffPushPrompt(role)
    setDismissed(true)
  }

  const handleDismiss = () => {
    dismissStaffPushPrompt(role)
    setDismissed(true)
  }

  return (
    <div className="fixed bottom-[calc(1rem+env(safe-area-inset-bottom))] left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
      <div className="pointer-events-auto w-full max-w-sm bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-4 flex gap-3 items-start">
        <Bell className="w-6 h-6 text-brand-400 shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-100">Turn on push notifications?</p>
          <p className="text-xs text-slate-400 mt-0.5">
            Get alerts for new items, claims, and drop-off events — even when the dashboard is closed.
          </p>
          <div className="flex gap-2 mt-3">
            <button
              type="button"
              onClick={handleAccept}
              disabled={loading}
              className="flex-1 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold py-2 rounded-lg disabled:opacity-60"
            >
              {loading ? 'Enabling…' : 'Accept'}
            </button>
            <button
              type="button"
              onClick={handleDismiss}
              className="flex-1 border border-slate-600 text-slate-400 text-xs font-semibold py-2 rounded-lg hover:bg-slate-800"
            >
              Not now
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
