/**
 * Root admin TOTP step — reached from unified /login (Section 4.6).
 */
import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/authService'
import { getAdminSecret, isAdminRole } from '../services/adminService'
import AuthLayout from '../components/AuthLayout'

export default function AdminTotpPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { totpVerify } = useAuth()
  const sessionToken = location.state?.sessionToken

  const [totpCode, setTotpCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  if (!sessionToken) {
    return (
      <AuthLayout>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Your sign-in session expired. Please log in again.
        </p>
        <Link to="/login" className="btn-primary w-full text-center block">Back to login</Link>
      </AuthLayout>
    )
  }

  async function handleTotp(e) {
    e.preventDefault()
    if (!totpCode.trim() || totpCode.length !== 6) {
      setErrors({ totp: 'Enter your 6-digit authenticator code' })
      return
    }

    setLoading(true)
    setErrors({})
    try {
      await totpVerify(sessionToken, totpCode)
      const me = await authService.getMe()
      if (!isAdminRole(me.role)) {
        navigate('/', { replace: true })
        return
      }
      const secret = getAdminSecret()
      navigate(secret ? `/admin/${secret}/dashboard` : '/', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Invalid 2FA code. Please try again.'
      setErrors({ totp: detail })
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          Admin two-factor authentication
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Enter the 6-digit code from your authenticator app
        </p>
      </div>

      <form onSubmit={handleTotp} className="space-y-4">
        <div>
          <label className="label" htmlFor="totp">Authenticator code</label>
          <input
            id="totp"
            type="text"
            inputMode="numeric"
            className="input text-center text-2xl tracking-[0.5em] font-bold"
            maxLength={6}
            placeholder="000000"
            value={totpCode}
            onChange={(e) => {
              setTotpCode(e.target.value.replace(/\D/g, ''))
              setErrors({})
            }}
            autoFocus
          />
          {errors.totp && <p className="error-text">{errors.totp}</p>}
        </div>

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Verifying…' : 'Verify'}
        </button>

        <Link to="/login" className="btn-ghost w-full text-center block text-slate-500">
          ← Back to login
        </Link>
      </form>
    </AuthLayout>
  )
}
