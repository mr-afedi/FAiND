import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { setAccessToken, clearAccessToken } from '../services/api'
import { authService } from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const navigate = useNavigate()
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  const SESSION_FLAG = 'faind_has_session'

  const _setSession = useCallback((accessToken, userObj) => {
    setAccessToken(accessToken)
    setUser(userObj)
    localStorage.setItem(SESSION_FLAG, '1')
  }, [])

  const _clearSession = useCallback(() => {
    clearAccessToken()
    setUser(null)
    localStorage.removeItem(SESSION_FLAG)
  }, [])

  // ── On hard reload: attempt silent token refresh ──────────────────────────
  useEffect(() => {
    const mayHaveSession = localStorage.getItem(SESSION_FLAG) === '1'

    if (!mayHaveSession) {
      setLoading(false)
      return
    }

    ;(async () => {
      try {
        const base = import.meta.env.VITE_API_URL || '/api/v1'
        const { data } = await axios.post(
          `${base}/auth/refresh`,
          {},
          { withCredentials: true }
        )
        setAccessToken(data.access_token)
        const me = await authService.getMe()
        setUser(me)
        localStorage.setItem(SESSION_FLAG, '1')
      } catch {
        _clearSession()
      } finally {
        setLoading(false)
      }
    })()
  }, [_clearSession])

  // ── Auth expiry (emitted by Axios interceptor) ────────────────────────────
  // IMPORTANT: do NOT call navigate() here synchronously.
  // navigate() fires before React commits setUser(null), so GuestRoute would
  // still see isAuthenticated=true and redirect straight to "/".
  // Instead we only clear state; ProtectedRoute detects isAuthenticated=false
  // on its next render and handles the redirect to /login itself.
  useEffect(() => {
    const handler = () => { _clearSession() }
    window.addEventListener('faind:auth:expired', handler)
    return () => window.removeEventListener('faind:auth:expired', handler)
  }, [_clearSession])

  // ── Public auth methods ───────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const data = await authService.login(email, password)
    if (data.requires_totp) {
      return { requiresTotp: true, sessionToken: data.session_token }
    }
    _setSession(data.access_token, data.user)
    return { requiresTotp: false }
  }, [_setSession])

  const totpVerify = useCallback(async (sessionToken, totpCode) => {
    const data = await authService.totpVerify(sessionToken, totpCode)
    _setSession(data.access_token, data.user)
  }, [_setSession])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } catch {
      // ignore — clear local state regardless
    } finally {
      _clearSession()
      // Defer navigate until after React commits user=null.
      // Calling navigate() synchronously here would cause GuestRoute at /login
      // to still see isAuthenticated=true (stale) and redirect to "/".
      setTimeout(() => navigate('/login', { replace: true }), 0)
    }
  }, [_clearSession, navigate])

  const afterEmailVerification = useCallback((accessToken, userObj) => {
    _setSession(accessToken, userObj)
  }, [_setSession])

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    totpVerify,
    logout,
    afterEmailVerification,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
