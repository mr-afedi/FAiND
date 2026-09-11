/**
 * Redirects authenticated users away from auth pages (login, signup, etc.)
 */
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function GuestRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent
                        rounded-full animate-spin" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return children
}
