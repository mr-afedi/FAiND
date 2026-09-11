/**
 * Mobile navigation drawer — hamburger menu for screens ≤768px.
 * Rendered via portal on document.body so it stacks above all page content.
 */
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function MobileNavMenuButton({ open, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="md:hidden w-10 h-10 rounded-xl flex items-center justify-center
                 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
      aria-label={open ? 'Close menu' : 'Open menu'}
      aria-expanded={open}
    >
      {open ? <X className="w-6 h-6" strokeWidth={1.75} /> : <Menu className="w-6 h-6" strokeWidth={1.75} />}
    </button>
  )
}

export default function MobileNavDrawer({ open, onClose }) {
  const { user, isAuthenticated, logout } = useAuth()

  useEffect(() => {
    if (!open) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : user?.username?.[0]?.toUpperCase() || '?'

  if (!open) return null

  return createPortal(
    <>
      <button
        type="button"
        className="fixed inset-0 z-[9998] bg-black/50 md:hidden"
        aria-label="Close menu"
        onClick={onClose}
      />
      <aside
        className="fixed top-0 right-0 z-[9999] h-full w-[min(100%,20rem)] md:hidden
                   bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800
                   shadow-2xl flex flex-col"
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-800">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">Menu</span>
          <button
            type="button"
            onClick={onClose}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-4 flex flex-col gap-1">
          {isAuthenticated ? (
            <>
              <div className="flex items-center gap-3 px-3 py-3 mb-2 rounded-xl bg-slate-50 dark:bg-slate-800/60">
                {user?.profile_photo_url ? (
                  <img src={user.profile_photo_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center text-white text-sm font-semibold">
                    {initials}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                    {user?.full_name || user?.username}
                  </p>
                  <p className="text-xs text-slate-500 truncate">@{user?.username}</p>
                </div>
              </div>
              <DrawerLink to="/dashboard" onClick={onClose}>Dashboard</DrawerLink>
              <DrawerLink to="/lost" onClick={onClose}>Lost Items</DrawerLink>
              <DrawerLink to="/found" onClick={onClose}>Found Items</DrawerLink>
              <DrawerLink to="/settings" onClick={onClose}>Settings</DrawerLink>
              <button
                type="button"
                onClick={() => { onClose(); logout() }}
                className="w-full text-left px-4 py-3 rounded-xl text-sm font-medium text-red-600 dark:text-red-400
                           hover:bg-red-50 dark:hover:bg-red-900/20 mt-2"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={onClose} className="btn-primary text-center text-sm py-3 mb-2">
                Log in
              </Link>
              <Link to="/signup" onClick={onClose} className="btn-secondary text-center text-sm py-3 mb-4">
                Sign up
              </Link>
              <DrawerLink to="/lost" onClick={onClose}>Lost Items</DrawerLink>
              <DrawerLink to="/found" onClick={onClose}>Found Items</DrawerLink>
              <DrawerLink to="/found" onClick={onClose}>Track a Found Item</DrawerLink>
            </>
          )}
        </nav>

        {!isAuthenticated && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-800">
            <Link
              to="/login"
              onClick={onClose}
              className="block text-center text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 py-2"
            >
              Authority / Staff Login
            </Link>
          </div>
        )}
      </aside>
    </>,
    document.body
  )
}

function DrawerLink({ to, onClick, children }) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="block px-4 py-3 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200
                 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
    >
      {children}
    </Link>
  )
}
