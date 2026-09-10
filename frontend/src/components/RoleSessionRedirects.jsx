/**
 * Auto-redirect staff sessions — authority, supervisor, and admin (Section 16).
 */
import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'
import { useAuth } from '../context/AuthContext'
import { isAdminRole, getAdminSecret } from '../services/adminService'

function useStaffAutoRedirect({ loading, isAuthenticated, dashboardPath, pathPrefix }) {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (loading || !isAuthenticated) return
    if (location.pathname.startsWith(pathPrefix)) return
    navigate(dashboardPath, { replace: true })
  }, [loading, isAuthenticated, location.pathname, navigate, dashboardPath, pathPrefix])
}

export function AuthoritySessionRedirect() {
  const { loading, isAuthorityAuthenticated } = useAuthorityAuth()
  useStaffAutoRedirect({
    loading,
    isAuthenticated: isAuthorityAuthenticated,
    dashboardPath: '/authority/dashboard',
    pathPrefix: '/authority/',
  })
  return null
}

export function SupervisorSessionRedirect() {
  const { loading, isSupervisorAuthenticated } = useSupervisorAuth()
  useStaffAutoRedirect({
    loading,
    isAuthenticated: isSupervisorAuthenticated,
    dashboardPath: '/supervisor/dashboard',
    pathPrefix: '/supervisor/',
  })
  return null
}

export function AdminSessionRedirect() {
  const { loading, isAuthenticated, user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const secret = getAdminSecret()
  const isAdmin = isAuthenticated && isAdminRole(user?.role) && Boolean(secret)

  useEffect(() => {
    if (loading || !isAdmin) return
    const adminPrefix = `/admin/${secret}`
    if (location.pathname.startsWith(adminPrefix)) return
    if (location.pathname === '/admin/totp') return
    if (location.pathname === '/login') return
    navigate(`${adminPrefix}/dashboard`, { replace: true })
  }, [loading, isAdmin, location.pathname, navigate, secret])

  return null
}
