import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useStaffPushNotifications } from '../hooks/useStaffPushNotifications'
import {
  getStaffPushSettings,
  updateStaffPushSettings,
} from '../services/staffPushService'

function Toggle({ on, onChange, label, description }) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <div>
        <p className="text-sm font-medium text-slate-200">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        onClick={() => onChange(!on)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors
                    ${on ? 'bg-brand-600' : 'bg-slate-700'}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition
                      ${on ? 'translate-x-5' : 'translate-x-0'}`}
        />
      </button>
    </div>
  )
}

export default function StaffPushSettingsToggle({ role, dark = true }) {
  const queryClient = useQueryClient()
  const { isSubscribed, requestPermissionAndSubscribe, unsubscribe, loading } =
    useStaffPushNotifications(role)

  const { data: settings } = useQuery({
    queryKey: ['staff-push-settings', role],
    queryFn: () => getStaffPushSettings(role),
  })

  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    if (settings) setEnabled(settings.push_notifications_enabled)
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: (value) => updateStaffPushSettings(role, value),
    onSuccess: (data) => {
      queryClient.setQueryData(['staff-push-settings', role], data)
      toast.success('Push notification preference saved')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not save setting'),
  })

  async function handleToggle(next) {
    if (next && !isSubscribed) {
      const ok = await requestPermissionAndSubscribe()
      if (!ok) {
        toast.error('Browser permission is required for push notifications')
        return
      }
    }
    if (!next && isSubscribed) {
      await unsubscribe()
    }
    setEnabled(next)
    saveMutation.mutate(next)
  }

  const textClass = dark ? 'text-slate-200' : 'text-slate-800'

  return (
    <div className={dark ? '' : 'border border-slate-200 dark:border-slate-700 rounded-xl p-4'}>
      <p className={`text-sm font-semibold mb-2 ${textClass}`}>Push notifications</p>
      <Toggle
        on={enabled && isSubscribed}
        onChange={handleToggle}
        label="Enable push alerts"
        description="Off by default. Alerts for items, claims, and drop-off events at your scope."
      />
      {loading && <p className="text-xs text-slate-500 mt-1">Updating subscription…</p>}
    </div>
  )
}
