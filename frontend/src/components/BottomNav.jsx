/**
 * Mobile bottom navigation (max-width 768px) — WhatsApp-style app bar.
 * Hidden on desktop.
 */
import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Search, PartyPopper, LayoutDashboard } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Home', Icon: Home, match: (p) => p === '/' },
  { to: '/lost', label: 'Lost', Icon: Search, match: (p) => p.startsWith('/lost') },
  { to: '/found', label: 'Found', Icon: PartyPopper, match: (p) => p.startsWith('/found') },
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard, match: (p) => p.startsWith('/dashboard') || p.startsWith('/settings'), auth: true },
]

function isAdminPath(pathname) {
  return pathname.startsWith('/admin/')
}

function isAuthorityPath(pathname) {
  return pathname.startsWith('/authority/')
}

function isSupervisorPath(pathname) {
  return pathname.startsWith('/supervisor/')
}

function isGuestAuthPath(pathname) {
  return ['/login', '/signup', '/forgot-password', '/verify-email'].some((p) => pathname.startsWith(p))
}

export default function BottomNav() {
  const { pathname } = useLocation()
  const { isAuthenticated } = useAuth()

  const visible = !isAdminPath(pathname) && !isAuthorityPath(pathname) && !isSupervisorPath(pathname) && !isGuestAuthPath(pathname)

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

          return (
            <Link
              key={to}
              to={href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 min-h-[44px] px-1
                          transition-colors ${active
                            ? 'text-brand-600 dark:text-brand-400'
                            : 'text-slate-500 dark:text-slate-400'}`}
            >
              <Icon className="w-5 h-5" aria-hidden />
              <span className="text-[10px] font-medium leading-none">{label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
