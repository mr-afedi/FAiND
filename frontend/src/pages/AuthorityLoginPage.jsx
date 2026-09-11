/**
 * Authority login — email/password then email OTP (Section 16.2).
 */
import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  authorityLogin,
  authorityVerifyOtp,
  getAuthorityMe,
  setAuthorityAccessToken,
  consumeAuthoritySessionExpired,
} from '../services/authorityService'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

export default function AuthorityLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { completeLogin, isAuthorityAuthenticated, loading } = useAuthorityAuth()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [sessionToken, setSessionToken] = useState(null)
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    if (consumeAuthoritySessionExpired() || location.state?.sessionExpired) {
      setSessionExpired(true)
      if (location.state?.sessionExpired) {
        navigate('/authority/login', { replace: true, state: {} })
      }
    }
  }, [location.state?.sessionExpired, navigate])

  useEffect(() => {
    if (!loading && isAuthorityAuthenticated) {
      navigate('/authority/dashboard', { replace: true })
    }
  }, [loading, isAuthorityAuthenticated, navigate])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (isAuthorityAuthenticated) return null

  async function handleLogin(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    try {
      const data = await authorityLogin(email.trim(), password)
      setSessionToken(data.session_token)
      toast.success('Check your email for the 6-digit code (see server console in dev).')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Sign-in failed')
    } finally {
      release()
    }
  }

  async function handleOtp(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    try {
      const data = await authorityVerifyOtp(sessionToken, otpCode.trim())
      setAuthorityAccessToken(data.access_token)
      const profile = await getAuthorityMe()
      completeLogin(data.access_token, profile)
      toast.success(`Signed in as ${profile.drop_point_name}`)
      navigate('/authority/dashboard', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid code')
    } finally {
      release()
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="glass w-full max-w-md p-8">
        <h1 className="text-xl font-bold text-slate-100 mb-1">FAiND Authority</h1>
        <p className="text-sm text-slate-400 mb-6">
          Drop point staff — use your <span className="text-slate-300">@gctu.edu.gh</span> email
        </p>

        {sessionExpired && (
          <p className="text-sm text-amber-300 bg-amber-900/30 border border-amber-800/50 rounded-lg px-3 py-2 mb-4">
            Your session has expired. Please log in again.
          </p>
        )}

        {!sessionToken ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input-field w-full"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@gctu.edu.gh"
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
              Continue
            </SubmitButton>
          </form>
        ) : (
          <form onSubmit={handleOtp} className="space-y-4">
            <p className="text-sm text-slate-400">
              Enter the 6-digit code sent to your email.
            </p>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              className="input-field w-full text-center tracking-widest text-lg"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
              required
            />
            <SubmitButton loading={isSubmitting} className="btn-primary w-full">
              Verify & sign in
            </SubmitButton>
            <button
              type="button"
              className="text-xs text-slate-500 hover:text-slate-300 w-full"
              onClick={() => { setSessionToken(null); setOtpCode('') }}
            >
              ← Back to password
            </button>
          </form>
        )}

        <p className="text-xs text-slate-500 mt-6 text-center">
          <Link to="/" className="hover:text-slate-300">← Back to FAiND</Link>
        </p>
      </div>
    </div>
  )
}
