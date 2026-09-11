import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import { authService } from '../services/authService'
import { useAuth } from '../context/AuthContext'

const RESEND_COOLDOWN = 60
const VERIFY_EMAIL_KEY = 'faind_verify_email'

export default function VerifyEmailPage() {
  const location  = useLocation()
  const navigate  = useNavigate()
  const { afterEmailVerification } = useAuth()

  const [email, setEmail]         = useState(
    () => location.state?.email || sessionStorage.getItem(VERIFY_EMAIL_KEY) || '',
  )
  const [code, setCode]           = useState(['', '', '', '', '', ''])
  const [loading, setLoading]     = useState(false)
  const [resending, setResending] = useState(false)
  const [cooldown, setCooldown]   = useState(0)
  const [error, setError]         = useState('')
  const inputRefs = useRef([])

  // On signup → code already sent, just start the cooldown timer.
  // On login redirect (fromLogin flag) → auto-request a fresh code immediately.
  useEffect(() => {
    const resolvedEmail = location.state?.email || sessionStorage.getItem(VERIFY_EMAIL_KEY)
    if (!resolvedEmail) return
    sessionStorage.setItem(VERIFY_EMAIL_KEY, resolvedEmail)
    if (location.state?.fromLogin) {
      // Came from login with an unverified account — request a fresh code silently
      authService.resendVerification(resolvedEmail).catch(() => {})
    }
    startCooldown()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const startCooldown = () => {
    setCooldown(RESEND_COOLDOWN)
  }

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  const handleCodeChange = (index, value) => {
    if (!/^\d?$/.test(value)) return
    const next = [...code]
    next[index] = value
    setCode(next)
    setError('')
    // Auto-advance
    if (value && index < 5) inputRefs.current[index + 1]?.focus()
  }

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e) => {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (text.length === 6) {
      setCode(text.split(''))
      inputRefs.current[5]?.focus()
      e.preventDefault()
    }
  }

  const handleVerify = async () => {
    const fullCode = code.join('')
    if (fullCode.length !== 6) {
      setError('Please enter the full 6-digit code')
      return
    }
    if (!email) {
      setError('Email address is required')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await authService.verifyEmail(email, fullCode)
      sessionStorage.removeItem(VERIFY_EMAIL_KEY)
      toast.success('Email verified! Welcome to FAiND.')
      afterEmailVerification(data.access_token, data.user)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Verification failed. Please try again.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (!email) { setError('Please enter your email address'); return }
    if (cooldown > 0) return

    setResending(true)
    try {
      await authService.resendVerification(email)
      toast.success('A new code has been sent to your email.')
      startCooldown()
      setCode(['', '', '', '', '', ''])
      inputRefs.current[0]?.focus()
    } catch (err) {
      const detail = err.response?.data?.detail || 'Could not resend code. Please try again.'
      toast.error(detail)
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthLayout>
      <div className="text-center mb-6">
        <div className="w-14 h-14 bg-brand-100 dark:bg-brand-900/30 rounded-2xl
                        flex items-center justify-center mx-auto mb-4">
          <svg className="w-7 h-7 text-brand-600 dark:text-brand-400" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round"
                  d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
          Verify your email
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          We sent a 6-digit code to{' '}
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {email || 'your email'}
          </span>
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
          Code expires in 15 minutes
        </p>
        {location.state?.tokensClaimed > 0 && (
          <p className="text-sm text-brand-600 dark:text-brand-400 mt-3">
            Your {location.state.tokensClaimed} finder tokens are saved — verify your email to access your dashboard.
          </p>
        )}
      </div>

      {/* Email input if not pre-filled */}
      {!email && (
        <div className="mb-4">
          <label className="label" htmlFor="verify-email">Email address</label>
          <input
            id="verify-email" type="email" className="input"
            placeholder="your@live.gctu.edu.gh"
            value={email} onChange={(e) => setEmail(e.target.value)}
          />
        </div>
      )}

      {/* 6-digit code input */}
      <div className="flex justify-center gap-2 mb-4" onPaste={handlePaste}>
        {code.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (inputRefs.current[i] = el)}
            type="text" inputMode="numeric" maxLength={1}
            className={`w-11 h-14 text-center text-xl font-bold rounded-xl border-2
                        bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100
                        transition-all duration-150 focus:outline-none
                        ${error
                          ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-400/30'
                          : 'border-slate-200 dark:border-slate-700 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20'
                        }`}
            value={digit}
            onChange={(e) => handleCodeChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
          />
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 text-center mb-3">{error}</p>
      )}

      <button
        className="btn-primary w-full"
        onClick={handleVerify}
        disabled={loading || code.join('').length !== 6}
      >
        {loading ? 'Verifying…' : 'Verify Email'}
      </button>

      <div className="mt-4 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Didn&apos;t receive it?{' '}
          <button
            className={`font-medium text-sm transition-colors duration-150
              ${cooldown > 0 || resending
                ? 'text-slate-400 cursor-not-allowed'
                : 'text-brand-600 dark:text-brand-400 hover:underline cursor-pointer'
              }`}
            onClick={handleResend}
            disabled={cooldown > 0 || resending}
          >
            {resending
              ? 'Sending…'
              : cooldown > 0
              ? `Resend Code (${cooldown}s)`
              : 'Resend Code'}
          </button>
        </p>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 text-center">
        <Link
          to="/signup"
          className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          ← Back to sign up
        </Link>
      </div>
    </AuthLayout>
  )
}
