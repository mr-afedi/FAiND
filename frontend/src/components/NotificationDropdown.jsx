/**
 * NotificationDropdown — bell icon with unread badge + dropdown panel.
 * Section 11.5: clicking marks read and navigates to relevant page.
 */
import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import useIsMobile from '../hooks/useIsMobile'
import {
  getMyNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
  clearDeletableNotifications,
} from '../services/matchService'
import { getItemDetail } from '../services/itemService'
import { invalidateAfterNotificationChange } from '../utils/queryCache'
import { NotificationTypeIcon, Bell, Trash2 } from './icons'
import ExpandableText from './ExpandableText'

const ITEM_LINK_RE = /^\/items\/([0-9a-f-]{36})$/i

function NotificationsPanel({
  unreadCount,
  deletableCount,
  isLoading,
  notifications,
  onClearAll,
  clearPending,
  onMarkAll,
  markAllPending,
  onNotificationClick,
  onDelete,
  deletePending,
  onViewAll,
  className = '',
}) {
  return (
    <div className={`overflow-hidden flex flex-col ${className}`}>
      <div className="flex items-center justify-between px-4 py-3
                      border-b border-slate-100 dark:border-slate-800">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">Notifications</h3>
        <div className="flex items-center gap-3">
          {deletableCount > 0 && (
            <button
              type="button"
              onClick={onClearAll}
              disabled={clearPending}
              className="text-xs text-slate-500 dark:text-slate-400 hover:text-red-600
                         dark:hover:text-red-400 hover:underline disabled:opacity-50"
            >
              Clear all
            </button>
          )}
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={onMarkAll}
              disabled={markAllPending}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline
                         disabled:opacity-50"
            >
              Mark all as read
            </button>
          )}
        </div>
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
              onNavigate={onNotificationClick}
              onDelete={onDelete}
              isDeleting={deletePending}
            />
          ))
        )}
      </div>

      <div className="border-t border-slate-100 dark:border-slate-800 px-4 py-2.5">
        <button
          type="button"
          onClick={onViewAll}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline w-full text-center"
        >
          View all in Dashboard →
        </button>
      </div>
    </div>
  )
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

function NotificationRow({ notif, onNavigate, onDelete, isDeleting }) {
  const isDimmed = !notif.deletable && notif.read

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
                  ${!notif.read ? 'bg-blue-50/60 dark:bg-blue-900/10' : ''}
                  ${isDimmed ? 'opacity-55' : ''}`}
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
        <ExpandableText
          text={notif.body}
          className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 break-words"
        />
        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
          {timeAgo(notif.created_at)}
        </p>
      </div>
      <div className="flex flex-col items-center gap-1.5 flex-shrink-0 mt-0.5">
        {!notif.read && (
          <span className="w-2 h-2 rounded-full bg-blue-500" />
        )}
        {notif.deletable && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(notif.id)
            }}
            disabled={isDeleting}
            className="p-1 rounded-md text-slate-400 hover:text-red-500
                       hover:bg-red-50 dark:hover:bg-red-900/20
                       disabled:opacity-40 transition-colors"
            aria-label="Delete notification"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.75} aria-hidden />
          </button>
        )}
      </div>
    </div>
  )
}

export default function NotificationDropdown() {
  const { isAuthenticated, authReady } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isMobile = useIsMobile()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (isMobile) return undefined
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isMobile])

  const { data } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: getMyNotifications,
    enabled: isAuthenticated && authReady,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: listData, isLoading } = useQuery({
    queryKey: ['notifications-list'],
    queryFn: () => getMyNotifications({ limit: 20 }),
    enabled: isAuthenticated && authReady && open,
    staleTime: 15_000,
  })

  const unreadCount = data?.unread_count ?? 0
  const notifications = listData?.notifications ?? []
  const deletableCount = notifications.filter((n) => n.deletable).length

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => invalidateAfterNotificationChange(queryClient),
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => invalidateAfterNotificationChange(queryClient),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteNotification,
    onSuccess: () => invalidateAfterNotificationChange(queryClient),
  })

  const clearAllMutation = useMutation({
    mutationFn: clearDeletableNotifications,
    onSuccess: () => invalidateAfterNotificationChange(queryClient),
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

  const panelProps = {
    unreadCount,
    deletableCount,
    isLoading,
    notifications,
    onClearAll: () => clearAllMutation.mutate(),
    clearPending: clearAllMutation.isPending,
    onMarkAll: () => markAllMutation.mutate(),
    markAllPending: markAllMutation.isPending,
    onNotificationClick: handleNotificationClick,
    onDelete: (id) => deleteMutation.mutate(id),
    deletePending: deleteMutation.isPending,
    onViewAll: () => { setOpen(false); navigate('/dashboard?tab=pending') },
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
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

      {open && isMobile && createPortal(
        <>
          <button
            type="button"
            className="fixed inset-0 z-[9998] bg-black/30 md:hidden"
            aria-label="Close notifications"
            onClick={() => setOpen(false)}
          />
          <NotificationsPanel
            {...panelProps}
            className="fixed z-[9999] left-0 right-0 w-full max-h-[calc(100vh-4rem)]
                       top-16 rounded-none border-t border-slate-200/80 dark:border-slate-700/60
                       bg-white dark:bg-slate-900 shadow-xl md:hidden"
          />
        </>,
        document.body
      )}

      {open && !isMobile && (
        <NotificationsPanel
          {...panelProps}
          className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[70vh]
                     rounded-2xl border border-slate-200/80 dark:border-slate-700/60
                     bg-white dark:bg-slate-900 shadow-xl z-50"
        />
      )}
    </div>
  )
}
