/**
 * Supervisor alerts bell — same read/delete rules as authority alerts.
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSupervisorAlerts,
  markSupervisorAlertRead,
  markAllSupervisorAlertsRead,
  deleteSupervisorAlert,
  clearDeletableSupervisorAlerts,
} from '../services/supervisorService'
import { Bell, Trash2 } from './icons'
import ExpandableText from './ExpandableText'

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function AlertRow({ alert, onNavigate, onDelete, isDeleting }) {
  const isDimmed = !alert.deletable && alert.read

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onNavigate(alert)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onNavigate(alert)
        }
      }}
      className={`w-full text-left px-4 py-3 flex gap-3 items-start cursor-pointer
                  hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors
                  ${!alert.read ? 'bg-brand-600/10' : ''}
                  ${isDimmed ? 'opacity-55' : ''}`}
    >
      <div className="flex-1 min-w-0">
        <p className={`text-sm leading-snug break-words
                      ${alert.read
                        ? 'text-slate-600 dark:text-slate-300'
                        : 'font-semibold text-slate-900 dark:text-slate-100'}`}>
          {alert.title}
        </p>
        <ExpandableText
          text={alert.body}
          className="text-xs text-slate-500 mt-0.5 break-words"
          buttonClassName="text-xs font-medium text-brand-500 dark:text-brand-400 hover:underline mt-1"
        />
        <p className="text-[10px] text-slate-400 dark:text-slate-600 mt-1">{timeAgo(alert.created_at)}</p>
      </div>
      <div className="flex flex-col items-center gap-1.5 flex-shrink-0 mt-0.5">
        {!alert.read && <span className="w-2 h-2 rounded-full bg-brand-500" />}
        {alert.deletable && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(alert.id)
            }}
            disabled={isDeleting}
            className="p-1 rounded-md text-slate-500 hover:text-red-500 dark:hover:text-red-400
                       hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-40 transition-colors"
            aria-label="Delete alert"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.75} aria-hidden />
          </button>
        )}
      </div>
    </div>
  )
}

export function parseSupervisorLink(link) {
  if (!link || !link.startsWith('supervisor:')) return null
  const rest = link.slice('supervisor:'.length)
  const colon = rest.indexOf(':')
  if (colon === -1) return { tab: rest, itemId: null }
  return { tab: rest.slice(0, colon), itemId: rest.slice(colon + 1) }
}

export default function SupervisorAlertsBell({ onNavigate }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const { data: summary } = useQuery({
    queryKey: ['supervisor-alerts-summary'],
    queryFn: () => getSupervisorAlerts({ limit: 1 }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: listData, isLoading } = useQuery({
    queryKey: ['supervisor-alerts-list'],
    queryFn: () => getSupervisorAlerts({ limit: 50 }),
    enabled: open,
    staleTime: 15_000,
  })

  const unreadCount = summary?.unread_count ?? 0
  const alerts = listData?.alerts ?? []
  const deletableCount = alerts.filter((a) => a.deletable).length

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['supervisor-alerts-summary'] })
    queryClient.invalidateQueries({ queryKey: ['supervisor-alerts-list'] })
  }

  const markReadMutation = useMutation({
    mutationFn: markSupervisorAlertRead,
    onSuccess: invalidate,
  })

  const markAllMutation = useMutation({
    mutationFn: markAllSupervisorAlertsRead,
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSupervisorAlert,
    onSuccess: invalidate,
  })

  const clearAllMutation = useMutation({
    mutationFn: clearDeletableSupervisorAlerts,
    onSuccess: invalidate,
  })

  const handleAlertClick = (alert) => {
    if (!alert.read) markReadMutation.mutate(alert.id)
    setOpen(false)
    if (alert.link && onNavigate) {
      onNavigate(parseSupervisorLink(alert.link))
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-9 h-9 rounded-xl flex items-center justify-center relative
                   text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        aria-label="Supervisor alerts"
      >
        <Bell className="w-5 h-5" strokeWidth={1.5} aria-hidden />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1
                           bg-red-500 text-white text-[10px] font-bold
                           rounded-full flex items-center justify-center leading-none">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
          <div
            className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[70vh] overflow-hidden
                       rounded-2xl border border-slate-200 dark:border-slate-700
                       bg-white dark:bg-slate-900 shadow-xl z-50 flex flex-col"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Alerts</h3>
              <div className="flex items-center gap-3">
                {deletableCount > 0 && (
                  <button
                    type="button"
                    onClick={() => clearAllMutation.mutate()}
                    disabled={clearAllMutation.isPending}
                    className="text-xs text-slate-500 hover:text-red-500 dark:hover:text-red-400 hover:underline
                               disabled:opacity-50"
                  >
                    Clear all
                  </button>
                )}
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={() => markAllMutation.mutate()}
                    disabled={markAllMutation.isPending}
                    className="text-xs text-brand-600 dark:text-brand-400 hover:underline disabled:opacity-50"
                  >
                    Mark all read
                  </button>
                )}
              </div>
            </div>
            <div className="overflow-y-auto flex-1">
              {isLoading && (
                <p className="text-sm text-slate-500 text-center py-8">Loading…</p>
              )}
              {!isLoading && alerts.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-8">No alerts yet.</p>
              )}
              {alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onNavigate={handleAlertClick}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  isDeleting={deleteMutation.isPending}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
