/**
 * Mobile bottom navigation (max-width 768px) — WhatsApp-style app bar.
 * Hidden on desktop and on full-screen chat threads.
 */
import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Search, PartyPopper, MessageCircle, LayoutDashboard } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useQuery } from '@tanstack/react-query'
import { getUnreadMessageCount } from '../services/messageService'

const NAV_ITEMS = [
  { to: '/', label: 'Home', Icon: Home, match: (p) => p === '/' },
  { to: '/lost', label: 'Lost', Icon: Search, match: (p) => p.startsWith('/lost') },
  { to: '/found', label: 'Found', Icon: PartyPopper, match: (p) => p.startsWith('/found') },
  { to: '/messages', label: 'Messages', Icon: MessageCircle, match: (p) => p.startsWith('/messages'), auth: true },
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard, match: (p) => p.startsWith('/dashboard') || p.startsWith('/settings'), auth: true },
]

function isAdminPath(pathname) {
  return pathname.startsWith('/admin/')
}

function isGuestAuthPath(pathname) {
  return ['/login', '/signup', '/forgot-password', '/verify-email'].some((p) => pathname.startsWith(p))
}

function isFullScreenChat(pathname) {
  return /^\/messages\/[^/]+/.test(pathname)
}

export default function BottomNav() {
  const { pathname } = useLocation()
  const { isAuthenticated, authReady } = useAuth()

  const { data: messagesUnread = 0 } = useQuery({
    queryKey: ['messages-unread-count'],
    queryFn: getUnreadMessageCount,
    enabled: isAuthenticated && authReady,
    staleTime: 5000,
  })

  const visible = !isAdminPath(pathname)
    && !isGuestAuthPath(pathname)
    && !isFullScreenChat(pathname)

  useEffect(() => {
    if (visible) {
      document.body.classList.add('mobile-bottom-nav')
    } else {
      document.body.classList.remove('mobile-bottom-nav')
    }
    return () => document.body.classList.remove('mobile-bottom-nav')
  }, [visible])

  if (!visible) return null

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-slate-200/80 dark:border-slate-800/80
                 bg-white/95 dark:bg-slate-950/95 backdrop-blur-lg
                 pb-[env(safe-area-inset-bottom,0px)]"
      aria-label="Main navigation"
    >
      <div className="flex items-stretch justify-around h-14">
        {NAV_ITEMS.map(({ to, label, Icon, match, auth }) => {
          const href = auth && !isAuthenticated ? '/login' : to
          const active = match(pathname)
          const showBadge = to === '/messages' && messagesUnread > 0

          return (
            <Link
              key={to}
              to={href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 min-h-[44px] px-1
                          transition-colors ${active
                            ? 'text-brand-600 dark:text-brand-400'
                            : 'text-slate-500 dark:text-slate-400'}`}
            >
              <span className="relative">
                <Icon className="w-5 h-5" aria-hidden />
                {showBadge && (
                  <span className="absolute -top-1 -right-2 min-w-[0.9rem] h-[0.9rem] px-0.5 rounded-full
                                   bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                    {messagesUnread > 9 ? '9+' : messagesUnread}
                  </span>
                )}
              </span>
              <span className="text-[10px] font-medium leading-none">{label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
