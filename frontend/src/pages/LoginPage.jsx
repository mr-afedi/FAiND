import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const navigate          = useNavigate()
  const location          = useLocation()
  const { login, totpVerify } = useAuth()

  // If the user arrived here WITHOUT a ProtectedRoute redirect (e.g. clicked
  // "Log in" directly), clear any stale sessionStorage redirect so they land
  // on the homepage after login, not some previously-visited protected page.
  useEffect(() => {
    if (!location.state?.from) {
      sessionStorage.removeItem('faind_login_redirect')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Priority: React Router state → sessionStorage fallback (survives login-page refresh) → home
  const from =
    location.state?.from?.pathname ||
    sessionStorage.getItem('faind_login_redirect') ||
    '/'

  // Step 1 — credentials
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  // Step 2 — TOTP (Root Admin only)
  const [totpStep, setTotpStep]         = useState(false)
  const [sessionToken, setSessionToken] = useState('')
  const [totpCode, setTotpCode]         = useState('')

  const [loading, setLoading] = useState(false)
  const [errors, setErrors]   = useState({})

  const handleCredentials = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    if (!password) errs.password = 'Password is required'
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    setErrors({})
    try {
      const result = await login(email.trim(), password)
      if (result.requiresTotp) {
        setSessionToken(result.sessionToken)
        setTotpStep(true)
        return
      }
      sessionStorage.removeItem('faind_login_redirect')
      navigate(from, { replace: true })
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
        || (err.code === 'ERR_NETWORK'
          ? 'Cannot reach the server. Make sure the backend is running (uvicorn on port 8000).'
          : 'Login failed. Please try again.')

      if (status === 403 && detail.toLowerCase().includes('verify')) {
        // Account exists but email not verified — send them straight to verify page
        navigate('/verify-email', { state: { email: email.trim(), fromLogin: true } })
      } else if (detail.toLowerCase().includes('incorrect') || status === 401) {
        setErrors({ credentials: 'Incorrect email or password.' })
      } else if (status === 403 && detail.toLowerCase().includes('suspended')) {
        setErrors({ credentials: detail })
      } else {
        toast.error(detail)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleTotp = async (e) => {
    e.preventDefault()
    if (!totpCode.trim() || totpCode.length !== 6) {
      setErrors({ totp: 'Enter your 6-digit authenticator code' })
      return
    }

    setLoading(true)
    setErrors({})
    try {
      await totpVerify(sessionToken, totpCode)
      sessionStorage.removeItem('faind_login_redirect')
      navigate(from, { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Invalid 2FA code. Please try again.'
      setErrors({ totp: detail })
    } finally {
      setLoading(false)
    }
  }

  if (totpStep) {
    return (
      <AuthLayout>
        <div className="text-center mb-6">
          <div className="w-14 h-14 bg-amber-100 dark:bg-amber-900/30 rounded-2xl
                          flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-amber-600 dark:text-amber-400" fill="none"
                 viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round"
                    d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            Two-factor authentication
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Enter the 6-digit code from your authenticator app
          </p>
        </div>

        <form onSubmit={handleTotp} className="space-y-4">
          <div>
            <label className="label" htmlFor="totp">Authenticator code</label>
            <input
              id="totp" type="text" inputMode="numeric"
              className="input text-center text-2xl tracking-[0.5em] font-bold"
              maxLength={6} placeholder="000000"
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

          <button
            type="button"
            className="btn-ghost w-full text-slate-500"
            onClick={() => { setTotpStep(false); setTotpCode(''); setErrors({}) }}
          >
            ← Back
          </button>
        </form>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Welcome back
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Don&apos;t have an account?{' '}
        <Link to="/signup" className="text-brand-600 hover:underline font-medium dark:text-brand-400">
          Sign up
        </Link>
      </p>

      <form onSubmit={handleCredentials} className="space-y-4" noValidate>
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email" type="email" className="input"
            placeholder="your@live.gctu.edu.gh"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setErrors({}) }}
            autoComplete="email"
          />
          {errors.email && <p className="error-text">{errors.email}</p>}
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="label mb-0" htmlFor="password">Password</label>
            <Link
              to="/forgot-password"
              className="text-xs text-brand-600 hover:underline dark:text-brand-400"
            >
              Forgot password?
            </Link>
          </div>
          <input
            id="password" type="password" className="input"
            placeholder="Your password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setErrors({}) }}
            autoComplete="current-password"
          />
          {errors.password && <p className="error-text">{errors.password}</p>}
        </div>

        {errors.credentials && (
          <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20
                         rounded-lg px-4 py-2.5">
            {errors.credentials}
          </p>
        )}

        <button type="submit" className="btn-primary w-full mt-2" disabled={loading}>
          {loading ? 'Logging in…' : 'Log In'}
        </button>
      </form>
    </AuthLayout>
  )
}
