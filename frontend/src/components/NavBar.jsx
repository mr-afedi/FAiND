import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import NotificationDropdown from './NotificationDropdown'
import ThemeToggleButton from './ThemeToggleButton'
import MessagesNavButton from './MessagesNavButton'
import MobileNavDrawer, { MobileNavMenuButton } from './MobileNavDrawer'

function AvatarDropdown({ user, onLogout }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : user?.username?.[0]?.toUpperCase() || '?'

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-xl px-2 py-1.5
                   hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-150"
      >
        {user?.profile_photo_url ? (
          <img src={user.profile_photo_url} alt={user.username}
               className="w-8 h-8 rounded-full object-cover" />
        ) : (
          <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center
                          text-white text-xs font-semibold">
            {initials}
          </div>
        )}
        <svg className={`w-4 h-4 text-slate-400 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
             fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-52 glass rounded-2xl shadow-xl
                        border border-slate-200/50 dark:border-slate-700/50
                        py-1.5 z-50 animate-fade-in">
          <div className="px-4 py-2 border-b border-slate-200/50 dark:border-slate-700/50">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
              {user?.full_name}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
              @{user?.username}
            </p>
          </div>

          <Link to={`/profile/${user?.username}`}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700
                           dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-slate-800/80
                           transition-colors duration-100">
            My Profile
          </Link>

          <Link to="/dashboard"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700
                           dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-slate-800/80
                           transition-colors duration-100">
            Dashboard
          </Link>

          <Link to="/settings"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700
                           dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-slate-800/80
                           transition-colors duration-100">
            Settings
          </Link>

          <div className="border-t border-slate-200/50 dark:border-slate-700/50 mt-1 pt-1">
            <button
              onClick={() => { setOpen(false); onLogout() }}
              className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-600
                         dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                         transition-colors duration-100">
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function NavBar() {
  const { user, isAuthenticated, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <nav className="sticky top-0 z-30 glass border-b border-slate-200/50 dark:border-slate-800/50">
      <div className="page-container flex items-center justify-between h-16">
        <Link to="/" className="text-xl font-bold tracking-tight flex-shrink-0">
          <span className="text-slate-700 dark:text-slate-200">FA</span>
          <span className="text-brand-500">i</span>
          <span className="text-slate-700 dark:text-slate-200">ND</span>
        </Link>

        <div className="hidden md:flex items-center gap-1">
          <Link to="/lost" className="px-3 py-2 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-150">
            Lost Items
          </Link>
          <Link to="/found" className="px-3 py-2 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-150">
            Found Items
          </Link>
          <Link to="/returned" className="px-3 py-2 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors duration-150">
            Returned
          </Link>
        </div>

        <div className="hidden md:flex items-center gap-2">
          <ThemeToggleButton />
          {isAuthenticated ? (
            <>
              <NotificationDropdown />
              <AvatarDropdown user={user} onLogout={logout} />
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost text-sm">Log in</Link>
              <Link to="/signup" className="btn-primary text-sm">Sign up</Link>
            </>
          )}
        </div>

        <div className="flex md:hidden items-center gap-0.5">
          <ThemeToggleButton />
          {isAuthenticated && (
            <>
              <NotificationDropdown />
              <MessagesNavButton />
            </>
          )}
          <MobileNavMenuButton open={mobileOpen} onToggle={() => setMobileOpen((o) => !o)} />
        </div>
      </div>

      <MobileNavDrawer open={mobileOpen} onClose={() => setMobileOpen(false)} />
    </nav>
  )
}
