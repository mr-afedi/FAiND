/**
 * Redirects authenticated users away from auth pages (login, signup, etc.)
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'
import { isAdminRole, getAdminSecret } from '../services/adminService'

const AUTH_FLOW_PATHS = new Set(['/authority/otp', '/admin/totp'])

export default function GuestRoute({ children }) {
  const location = useLocation()
  const onAuthFlowStep = AUTH_FLOW_PATHS.has(location.pathname)
  const { isAuthenticated, loading, user } = useAuth()
  const { isAuthorityAuthenticated, loading: authorityLoading } = useAuthorityAuth()
  const { isSupervisorAuthenticated, loading: supervisorLoading } = useSupervisorAuth()

  if (loading || authorityLoading || supervisorLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent
                        rounded-full animate-spin" />
      </div>
    )
  }

  if (isAuthorityAuthenticated && !onAuthFlowStep) {
    return <Navigate to="/authority/dashboard" replace />
  }

  if (isSupervisorAuthenticated && !onAuthFlowStep) {
    return <Navigate to="/supervisor/dashboard" replace />
  }

  if (isAuthenticated && !onAuthFlowStep) {
    if (isAdminRole(user?.role)) {
      const secret = getAdminSecret()
      if (secret) return <Navigate to={`/admin/${secret}/dashboard`} replace />
    }
    return <Navigate to="/dashboard" replace />
  }

  return children
}
