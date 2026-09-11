import { Navigate } from 'react-router-dom'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import { hasAuthoritySessionFlag, markAuthoritySessionExpired } from '../services/authorityService'

export default function AuthorityProtectedRoute({ children }) {
  const { isAuthorityAuthenticated, loading } = useAuthorityAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthorityAuthenticated) {
    let sessionExpired = false
    if (hasAuthoritySessionFlag()) {
      markAuthoritySessionExpired()
      sessionExpired = true
    }
    return <Navigate to="/login" state={{ sessionExpired }} replace />
  }

  return children
}
