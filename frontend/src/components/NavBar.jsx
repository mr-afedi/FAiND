import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { getMyNotifications } from '../services/matchService'

function ThemeToggle() {
  const { dark, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="w-9 h-9 rounded-xl flex items-center justify-center
                 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800
                 transition-colors duration-150"
      aria-label="Toggle theme"
    >
      {dark ? (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
        </svg>
      )}
    </button>
  )
}

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
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            My Profile
          </Link>

          <Link to="/dashboard"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700
                           dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-slate-800/80
                           transition-colors duration-100">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
            </svg>
            Dashboard
          </Link>

          <Link to="/settings"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700
                           dark:text-slate-300 hover:bg-slate-100/80 dark:hover:bg-slate-800/80
                           transition-colors duration-100">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            Settings
          </Link>

          <div className="border-t border-slate-200/50 dark:border-slate-700/50 mt-1 pt-1">
            <button
              onClick={() => { setOpen(false); onLogout() }}
              className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-600
                         dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                         transition-colors duration-100">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
              </svg>
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
  const navigate = useNavigate()

  const { data: notifData } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: getMyNotifications,
    enabled: isAuthenticated,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
  const unreadCount = notifData?.unread_count ?? 0

  return (
    <nav className="sticky top-0 z-30 glass border-b border-slate-200/50 dark:border-slate-800/50">
      <div className="page-container flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="text-xl font-bold tracking-tight flex-shrink-0">
          <span className="text-slate-700 dark:text-slate-200">FA</span>
          <span className="text-brand-500">i</span>
          <span className="text-slate-700 dark:text-slate-200">ND</span>
        </Link>

        {/* Centre nav links */}
        <div className="hidden sm:flex items-center gap-1">
          <Link to="/lost"
                className="px-3 py-2 rounded-xl text-sm font-medium text-slate-600
                           dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800
                           transition-colors duration-150">
            Lost Items
          </Link>
          <Link to="/found"
                className="px-3 py-2 rounded-xl text-sm font-medium text-slate-600
                           dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800
                           transition-colors duration-150">
            Found Items
          </Link>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2">
          <ThemeToggle />

          {isAuthenticated ? (
            <>
              {/* Bell — shows unread badge; full dropdown in Feature H */}
              <button
                onClick={() => navigate('/dashboard?tab=pending')}
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

              {/* Messages — placeholder, Feature L will wire this up */}
              <button
                onClick={() => navigate('/messages')}
                className="w-9 h-9 rounded-xl flex items-center justify-center relative
                           text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800
                           transition-colors duration-150"
                aria-label="Messages"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
                </svg>
              </button>

              <AvatarDropdown user={user} onLogout={logout} />
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost text-sm hidden sm:inline-flex">Log in</Link>
              <Link to="/signup" className="btn-primary text-sm">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
