import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Session-storage key used to survive a browser refresh of the login page
const REDIRECT_KEY = 'faind_login_redirect'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent
                        rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) {
    // Persist the intended path so it survives a login-page refresh
    sessionStorage.setItem(REDIRECT_KEY, location.pathname)
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
