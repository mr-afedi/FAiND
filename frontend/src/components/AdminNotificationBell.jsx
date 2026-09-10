/**
 * Admin notification bell — links use admin:{section}:{id} or admin:reports:{type}:{id}.
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import {
  getMyNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '../services/matchService'
import { invalidateAfterNotificationChange } from '../utils/queryCache'
import { Bell } from './icons'
import ExpandableText from './ExpandableText'

function parseAdminLink(link) {
  if (!link) return null
  const parts = link.split(':')
  if (parts[0] !== 'admin') return null
  if (parts.length === 3) {
    return { section: parts[1], id: parts[2], meta: {} }
  }
  if (parts.length === 4 && parts[1] === 'reports') {
    return { section: 'reports', id: parts[3], meta: { report_type: parts[2] } }
  }
  return null
}

function isAdminLink(link) {
  return parseAdminLink(link) !== null
}

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function AdminNotificationBell({ onNavigate, enabled = true }) {
  const { isAuthenticated, authReady } = useAuth()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const canFetch = enabled && isAuthenticated && authReady

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const { data: listData, isLoading } = useQuery({
    queryKey: ['notifications-list-admin'],
    queryFn: () => getMyNotifications({ limit: 50 }),
    enabled: canFetch,
    staleTime: 30_000,
    refetchInterval: canFetch ? 60_000 : false,
  })

  const notifications = (listData?.notifications ?? []).filter(
    (n) => n.link && isAdminLink(n.link),
  )
  const unreadCount = notifications.filter((n) => !n.read).length

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      invalidateAfterNotificationChange(queryClient)
      queryClient.invalidateQueries({ queryKey: ['notifications-list-admin'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      invalidateAfterNotificationChange(queryClient)
      queryClient.invalidateQueries({ queryKey: ['notifications-list-admin'] })
    },
  })

  const handleClick = (notif) => {
    if (!notif.read) markReadMutation.mutate(notif.id)
    setOpen(false)
    const parsed = parseAdminLink(notif.link)
    if (parsed && onNavigate) {
      onNavigate(parsed.section, parsed.id, parsed.meta)
    }
  }

  if (!canFetch) return null

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-9 h-9 rounded-xl flex items-center justify-center relative
                   text-slate-400 hover:bg-slate-800 transition-colors"
        aria-label="Admin notifications"
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
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[70vh] overflow-hidden
                       rounded-2xl border border-slate-700 bg-slate-900 shadow-xl z-50 flex flex-col"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100">Admin alerts</h3>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={() => markAllMutation.mutate()}
                  className="text-xs text-brand-400 hover:underline"
                >
                  Mark all as read
                </button>
              )}
            </div>
            <div className="overflow-y-auto flex-1">
              {isLoading ? (
                <div className="flex justify-center py-10">
                  <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : notifications.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-500">No admin alerts</p>
              ) : (
                notifications.map((notif) => (
                  <div
                    key={notif.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => handleClick(notif)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleClick(notif)
                      }
                    }}
                    className={`w-full text-left px-4 py-3 hover:bg-slate-800/60 transition-colors cursor-pointer
                                ${!notif.read ? 'bg-brand-600/10' : ''}`}
                  >
                    <p className={`text-sm ${!notif.read ? 'font-semibold text-slate-100' : 'text-slate-300'}`}>
                      {notif.title}
                    </p>
                    <ExpandableText
                      text={notif.body}
                      className="text-xs text-slate-500 mt-0.5"
                      buttonClassName="text-xs font-medium text-brand-400 hover:underline mt-1"
                    />
                    <p className="text-[10px] text-slate-600 mt-1">{timeAgo(notif.created_at)}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
