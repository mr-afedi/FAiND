import { Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { WifiOff } from '../components/icons'

export default function OfflinePage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-24 text-center">
        <div className="glass-card max-w-md mx-auto p-8">
          <WifiOff className="w-12 h-12 mx-auto text-amber-500 mb-4" aria-hidden />
          <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100 mb-2">
            You are offline
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            FAiND needs a live connection for items, matches, and messages.
            Reconnect to refresh your feed.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              type="button"
              className="btn-primary text-sm"
              onClick={() => window.location.reload()}
            >
              Try again
            </button>
            <Link to="/" className="btn-secondary text-sm">
              Go home
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
