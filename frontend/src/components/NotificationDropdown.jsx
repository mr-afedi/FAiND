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
import { getItemDetail } from '../services/itemService'
import { NotificationTypeIcon, Bell } from './icons'

const ITEM_LINK_RE = /^\/items\/([0-9a-f-]{36})$/i

function timeAgo(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

/** Approximate two lines of text-xs in the notification panel */
const BODY_TWO_LINE_CHARS = 100

function NotificationRow({ notif, onNavigate }) {
  const [expanded, setExpanded] = useState(false)
  const canExpand = (notif.body?.length ?? 0) > BODY_TWO_LINE_CHARS

  const handleRowClick = () => {
    onNavigate(notif)
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleRowClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleRowClick()
        }
      }}
      className={`w-full text-left px-4 py-3 flex gap-3 items-start cursor-pointer
                  hover:bg-slate-50 dark:hover:bg-slate-800/60
                  transition-colors duration-100
                  ${!notif.read ? 'bg-blue-50/60 dark:bg-blue-900/10' : ''}`}
    >
      <span className="mt-0.5 flex-shrink-0 text-slate-500 dark:text-slate-400">
        <NotificationTypeIcon type={notif.notification_type} />
      </span>
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm leading-snug break-words
                      ${notif.read
                        ? 'text-slate-700 dark:text-slate-300'
                        : 'font-semibold text-slate-900 dark:text-white'}`}
        >
          {notif.title}
        </p>
        <p
          className={`text-xs text-slate-500 dark:text-slate-400 mt-0.5 break-words
                      ${expanded ? '' : 'line-clamp-2'}`}
        >
          {notif.body}
        </p>
        {canExpand && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setExpanded((v) => !v)
            }}
            className="text-xs font-medium text-blue-600 dark:text-blue-400
                       hover:underline mt-1"
          >
            {expanded ? 'Show less' : 'Read more'}
          </button>
        )}
        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
          {timeAgo(notif.created_at)}
        </p>
      </div>
      {!notif.read && (
        <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-1.5" />
      )}
    </div>
  )
}

export default function NotificationDropdown() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
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

  const { data } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: getMyNotifications,
    enabled: isAuthenticated,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: listData, isLoading } = useQuery({
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

  const handleNotificationClick = async (notif) => {
    if (!notif.read) markReadMutation.mutate(notif.id)
    setOpen(false)
    if (!notif.link) return

    const itemLink = notif.link.match(ITEM_LINK_RE)
    if (itemLink) {
      try {
        await getItemDetail(itemLink[1])
        navigate(notif.link)
      } catch {
        navigate('/item-unavailable')
      }
      return
    }

    navigate(notif.link)
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
        <div
          className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[70vh] overflow-hidden
                     rounded-2xl border border-slate-200/80 dark:border-slate-700/60
                     bg-white dark:bg-slate-900 shadow-xl z-50 flex flex-col"
        >
          <div className="flex items-center justify-between px-4 py-3
                          border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1">
            {isLoading ? (
              <div className="flex justify-center py-10">
                <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-10 text-center text-sm text-slate-400">
                <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden />
                No notifications yet
              </div>
            ) : (
              notifications.map((notif) => (
                <NotificationRow
                  key={notif.id}
                  notif={notif}
                  onNavigate={handleNotificationClick}
                />
              ))
            )}
          </div>

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

      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden />
      )}
    </div>
  )
}
