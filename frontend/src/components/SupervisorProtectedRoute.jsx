import { Navigate, useLocation } from 'react-router-dom'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'

export default function SupervisorProtectedRoute({ children }) {
  const { isSupervisorAuthenticated, loading } = useSupervisorAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isSupervisorAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
