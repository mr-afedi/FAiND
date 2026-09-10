/**
 * Unified login — students, authorities, supervisors, and root admin (Section 5).
 */
import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/authService'
import { authorityLogin, consumeAuthoritySessionExpired, rememberAuthorityOtpSession } from '../services/authorityService'
import { supervisorLogin, getSupervisorMe, setSupervisorAccessToken } from '../services/supervisorService'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'
import { isAdminRole, getAdminSecret } from '../services/adminService'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const { completeLogin: completeSupervisorLogin } = useSupervisorAuth()

  useEffect(() => {
    if (!location.state?.from) {
      sessionStorage.removeItem('faind_login_redirect')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const from =
    location.state?.from?.pathname ||
    sessionStorage.getItem('faind_login_redirect') ||
    '/dashboard'

  const sessionExpired = Boolean(
    location.state?.sessionExpired || consumeAuthoritySessionExpired(),
  )

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

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
        navigate('/admin/totp', { replace: true, state: { sessionToken: result.sessionToken } })
        return
      }
      const me = await authService.getMe()
      sessionStorage.removeItem('faind_login_redirect')
      if (isAdminRole(me.role)) {
        const secret = getAdminSecret()
        navigate(secret ? `/admin/${secret}/dashboard` : from, { replace: true })
        return
      }
      navigate((!from || from === '/' || from === '/login') ? '/dashboard' : from, { replace: true })
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail

      if (status === 403 && detail?.toLowerCase?.().includes('verify')) {
        navigate('/verify-email', { state: { email: email.trim(), fromLogin: true } })
        return
      }

      if (status === 401 || detail?.toLowerCase?.().includes('incorrect')) {
        try {
          const authorityData = await authorityLogin(email.trim(), password)
          if (!authorityData?.session_token) {
            toast.error('Could not start authority sign-in. Please try again.')
            return
          }
          rememberAuthorityOtpSession(authorityData.session_token)
          toast.success('Check your email for the 6-digit code.')
          navigate('/authority/otp', { replace: true, state: { sessionToken: authorityData.session_token } })
          return
        } catch {
          /* try supervisor next */
        }

        try {
          const supervisorData = await supervisorLogin(email.trim(), password)
          setSupervisorAccessToken(supervisorData.access_token)
          const profile = await getSupervisorMe()
          completeSupervisorLogin(supervisorData.access_token, profile)
          toast.success('Signed in')
          navigate('/supervisor/dashboard', { replace: true })
          return
        } catch (supervisorErr) {
          const superDetail = supervisorErr.response?.data?.detail
          if (supervisorErr.response?.status === 403 && superDetail?.toLowerCase?.().includes('suspended')) {
            setErrors({ credentials: superDetail })
            return
          }
        }

        setErrors({ credentials: 'Incorrect email or password.' })
      } else if (status === 403 && detail?.toLowerCase?.().includes('suspended')) {
        setErrors({ credentials: detail })
      } else {
        toast.error(
          detail
          || (err.code === 'ERR_NETWORK'
            ? 'Cannot reach the server. Make sure the backend is running.'
            : 'Login failed. Please try again.'),
        )
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Welcome back
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Students, staff, and campus authorities sign in here.{' '}
        <Link to="/signup" className="text-brand-600 hover:underline font-medium dark:text-brand-400">
          Create a student account
        </Link>
      </p>

      {sessionExpired && (
        <p className="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20
                       border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-2.5 mb-4">
          Your session has expired. Please log in again.
        </p>
      )}

      <form onSubmit={handleCredentials} className="space-y-4" noValidate>
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            className="input"
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
            id="password"
            type="password"
            className="input"
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
