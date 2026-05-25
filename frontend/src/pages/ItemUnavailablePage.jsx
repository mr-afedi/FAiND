/**
 * Shown when a notification or link targets a deleted/archived item —
 * avoids loading ItemDetailPage for a missing resource.
 */
import { Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { EmptyInboxIcon } from '../components/icons'

export default function ItemUnavailablePage() {
  return (
    <>
      <NavBar />
      <div className="page-container py-20 text-center max-w-md mx-auto">
        <EmptyInboxIcon className="w-14 h-14 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-slate-700 dark:text-slate-300 mb-2">
          This item is no longer available
        </h1>
        <p className="text-sm text-slate-400 mb-8">
          It may have been removed, returned, or expired. You can still check your dashboard
          for other matches.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/" className="btn-secondary text-sm">Go Home</Link>
          <Link to="/dashboard" className="btn-primary text-sm">Go to Dashboard</Link>
        </div>
      </div>
    </>
  )
}
