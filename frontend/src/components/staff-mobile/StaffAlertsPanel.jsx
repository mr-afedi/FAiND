/**
 * Mobile alerts list with swipe-to-delete for staff dashboards.
 */
import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import {
  getAuthorityAlerts,
  markAuthorityAlertRead,
  markAllAuthorityAlertsRead,
  deleteAuthorityAlert,
  clearDeletableAuthorityAlerts,
} from '../../services/authorityService'
import { parseAuthorityLink } from '../AuthorityAlertsBell'
import ExpandableText from '../ExpandableText'

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function SwipeableAlertRow({ alert, onNavigate, onDelete, isDeleting }) {
  const [offset, setOffset] = useState(0)
  const startX = useRef(null)
  const swiped = useRef(false)
  const DELETE_WIDTH = 80

  function onTouchStart(e) {
    startX.current = e.touches[0].clientX
    swiped.current = false
  }

  function onTouchMove(e) {
    if (startX.current == null) return
    const dx = e.touches[0].clientX - startX.current
    if (dx < -10) swiped.current = true
    if (dx < 0 && alert.deletable) {
      setOffset(Math.max(dx, -DELETE_WIDTH))
    }
  }

  function onTouchEnd() {
    if (offset < -DELETE_WIDTH / 2) setOffset(-DELETE_WIDTH)
    else setOffset(0)
    startX.current = null
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-800/80">
      {alert.deletable && (
        <button
          type="button"
          onClick={() => onDelete(alert.id)}
          disabled={isDeleting}
          className="absolute inset-y-0 right-0 w-20 bg-red-600 flex flex-col items-center
                     justify-center text-white text-xs font-semibold gap-1"
        >
          <Trash2 className="w-5 h-5" aria-hidden />
          Delete
        </button>
      )}
      <div
        role="button"
        tabIndex={0}
        style={{ transform: `translateX(${offset}px)` }}
        className={`relative bg-slate-900/80 p-4 transition-transform
          ${!alert.read ? 'border-l-4 border-l-brand-500' : ''}`}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onClick={() => {
          if (swiped.current && offset < 0) return
          onNavigate(alert)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onNavigate(alert)
          }
        }}
      >
        <p className={`text-base leading-snug ${alert.read ? 'text-slate-700 dark:text-slate-300' : 'font-semibold text-slate-900 dark:text-slate-100'}`}>
          {alert.title}
        </p>
        <ExpandableText
          text={alert.body}
          className="text-sm text-slate-400 mt-1 leading-relaxed"
          buttonClassName="text-sm font-medium text-brand-400 hover:underline mt-2 min-h-[44px]"
        />
        <p className="text-sm text-slate-500 mt-2">{timeAgo(alert.created_at)}</p>
      </div>
    </div>
  )
}

export default function StaffAlertsPanel({ onNavigate }) {
  const queryClient = useQueryClient()

  const { data: listData, isLoading } = useQuery({
    queryKey: ['authority-alerts-list'],
    queryFn: () => getAuthorityAlerts({ limit: 50 }),
    staleTime: 15_000,
  })

  const alerts = listData?.alerts ?? []
  const unreadCount = listData?.unread_count ?? 0
  const deletableCount = alerts.filter((a) => a.deletable).length

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['authority-alerts-summary'] })
    queryClient.invalidateQueries({ queryKey: ['authority-alerts-list'] })
  }

  const markReadMutation = useMutation({
    mutationFn: markAuthorityAlertRead,
    onSuccess: invalidate,
  })

  const markAllMutation = useMutation({
    mutationFn: markAllAuthorityAlertsRead,
    onSuccess: invalidate,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAuthorityAlert,
    onSuccess: invalidate,
  })

  const clearAllMutation = useMutation({
    mutationFn: clearDeletableAuthorityAlerts,
    onSuccess: invalidate,
  })

  function handleClick(alert) {
    if (!alert.read) markReadMutation.mutate(alert.id)
    if (alert.link && onNavigate) onNavigate(parseAuthorityLink(alert.link))
  }

  return (
    <div className="md:hidden space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Alerts</h3>
        <div className="flex gap-3 text-sm">
          {deletableCount > 0 && (
            <button
              type="button"
              onClick={() => clearAllMutation.mutate()}
              disabled={clearAllMutation.isPending}
              className="text-slate-400 hover:text-red-400 min-h-[44px]"
            >
              Clear all
            </button>
          )}
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="text-brand-400 min-h-[44px]"
            >
              Mark all read
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : alerts.length === 0 ? (
        <p className="text-base text-slate-500 text-center py-8">No alerts yet</p>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <SwipeableAlertRow
              key={alert.id}
              alert={alert}
              onNavigate={handleClick}
              onDelete={(id) => deleteMutation.mutate(id)}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}
