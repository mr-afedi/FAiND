/**
 * NotificationDropdown — bell icon with unread badge + dropdown panel.
 * Section 11.5: clicking marks read and navigates to relevant page.
 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import {
  getMyNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from '../services/matchService'

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const TYPE_ICON = {
  match_found: '🔍',
  claim_received: '📩',
  verified: '✅',
  failed: '❌',
  returned: '🎉',
  dispute: '⚠️',
  tip: '💰',
  expiring: '⏰',
  suspended: '🚫',
}

export default function NotificationDropdown() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const { data } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: getMyNotifications,
    enabled: isAuthenticated,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: listData } = useQuery({
    queryKey: ['notifications-list'],
    queryFn: () => getMyNotifications({ limit: 20 }),
    enabled: isAuthenticated && open,
    staleTime: 15_000,
  })

  const unreadCount = data?.unread_count ?? 0
  const notifications = listData?.notifications ?? []

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
    },
  })

  const handleNotificationClick = (notif) => {
    if (!notif.read) markReadMutation.mutate(notif.id)
    setOpen(false)
    if (notif.link) navigate(notif.link)
  }

  if (!isAuthenticated) return null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-9 h-9 rounded-xl flex items-center justify-center relative
                   text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800
                   transition-colors duration-150"
        aria-label="Notifications"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1
                           bg-red-500 text-white text-[9px] font-bold rounded-full
                           flex items-center justify-center leading-none">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-900
                        border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl
                        z-50 overflow-hidden animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3
                          border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-white">
              Notifications
              {unreadCount > 0 && (
                <span className="ml-2 text-xs bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400
                                 px-1.5 py-0.5 rounded-full font-bold">
                  {unreadCount} new
                </span>
              )}
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800">
            {notifications.length === 0 ? (
              <div className="py-10 text-center">
                <p className="text-2xl mb-2">🔔</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  No notifications yet
                </p>
              </div>
            ) : (
              notifications.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`w-full text-left px-4 py-3 flex gap-3 items-start
                              hover:bg-slate-50 dark:hover:bg-slate-800/60
                              transition-colors duration-100
                              ${!notif.read ? 'bg-blue-50/60 dark:bg-blue-900/10' : ''}`}
                >
                  <span className="text-lg mt-0.5 flex-shrink-0">
                    {TYPE_ICON[notif.notification_type] || '🔔'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm leading-tight truncate
                                  ${notif.read
                                    ? 'text-slate-700 dark:text-slate-300'
                                    : 'font-semibold text-slate-900 dark:text-white'}`}>
                      {notif.title}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                      {notif.body}
                    </p>
                    <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {timeAgo(notif.created_at)}
                    </p>
                  </div>
                  {!notif.read && (
                    <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1.5" />
                  )}
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 dark:border-slate-800 px-4 py-2.5">
            <button
              onClick={() => { setOpen(false); navigate('/dashboard?tab=pending') }}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline w-full text-center"
            >
              View all in Dashboard →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
