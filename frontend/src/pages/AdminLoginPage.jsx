/**
 * Admin login — same credentials as main app; root admin requires TOTP (Section 4.6).
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/authService'
import {
  isValidAdminSecret,
  rememberAdminSecret,
  isAdminRole,
  getAdminSecret,
} from '../services/adminService'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

export default function AdminLoginPage() {
  const { adminSecret } = useParams()
  const navigate = useNavigate()
  const { login, totpVerify, user, loading, isAuthenticated } = useAuth()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [sessionToken, setSessionToken] = useState(null)

  useEffect(() => {
    if (!loading && isAuthenticated && isAdminRole(user?.role)) {
      navigate(`/admin/${getAdminSecret() || adminSecret}/dashboard`, { replace: true })
    }
  }, [loading, isAuthenticated, user?.role, navigate, adminSecret])

  if (!isValidAdminSecret(adminSecret)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-400">
        <p>404 — Not found</p>
      </div>
    )
  }

  rememberAdminSecret(adminSecret)

  if (loading || (isAuthenticated && isAdminRole(user?.role))) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  async function handleLogin(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    try {
      const result = await login(email, password)
      if (result.requiresTotp) {
        setSessionToken(result.sessionToken)
        release()
        return
      }
      const me = await authService.getMe()
      if (!isAdminRole(me.role)) {
        release()
        return navigate('/')
      }
      navigate(`/admin/${adminSecret}/dashboard`)
    } catch {
      release()
    }
  }

  async function handleTotp(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    try {
      await totpVerify(sessionToken, totpCode)
      const me = await authService.getMe()
      if (!isAdminRole(me.role)) {
        release()
        return navigate('/')
      }
      navigate(`/admin/${adminSecret}/dashboard`)
    } catch {
      release()
    } finally {
      release()
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="glass w-full max-w-md p-8">
        <h1 className="text-xl font-bold text-slate-100 mb-1">FAiND Admin</h1>
        <p className="text-sm text-slate-400 mb-6">Authorized personnel only</p>

        {!sessionToken ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input-field w-full"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input-field w-full"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <SubmitButton loading={isSubmitting} className="btn-primary w-full">
              Sign in
            </SubmitButton>
          </form>
        ) : (
          <form onSubmit={handleTotp} className="space-y-4">
            <p className="text-sm text-slate-400">Enter your 6-digit authenticator code.</p>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              className="input-field w-full text-center tracking-widest text-lg"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
              required
            />
            <SubmitButton loading={isSubmitting} className="btn-primary w-full">
              Verify 2FA
            </SubmitButton>
          </form>
        )}
      </div>
    </div>
  )
}
