import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import { authService } from '../services/authService'

// Multi-step: step 1 = enter email, step 2 = enter code + new password
export default function ForgotPasswordPage() {
  const navigate   = useNavigate()
  const [step, setStep]     = useState(1)
  const [email, setEmail]   = useState('')
  const [code, setCode]     = useState('')
  const [newPassword, setNewPassword]       = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors]   = useState({})

  const handleStep1 = async (e) => {
    e.preventDefault()
    if (!email.trim()) { setErrors({ email: 'Email is required' }); return }
    setLoading(true)
    setErrors({})
    try {
      await authService.forgotPassword(email.trim())
      toast.success('If an account exists, a reset code has been sent.')
      setStep(2)
    } catch {
      // Silent on unknown emails — don't reveal account existence
      toast.success('If an account exists, a reset code has been sent.')
      setStep(2)
    } finally {
      setLoading(false)
    }
  }

  const handleStep2 = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!code.trim() || code.length !== 6) errs.code = 'Enter the 6-digit code'
    if (!newPassword) errs.newPassword = 'New password is required'
    if (newPassword.length < 8) errs.newPassword = 'Password must be at least 8 characters'
    if (newPassword !== confirmPassword) errs.confirmPassword = 'Passwords do not match'
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    setErrors({})
    try {
      await authService.resetPassword(email, code, newPassword, confirmPassword)
      toast.success('Password reset! Please log in with your new password.')
      navigate('/login', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Reset failed. Please try again.'
      if (detail.toLowerCase().includes('code')) setErrors({ code: detail })
      else toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      {step === 1 ? (
        <>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
            Forgot your password?
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Enter your GCTU email and we&apos;ll send a reset code.
          </p>

          <form onSubmit={handleStep1} className="space-y-4" noValidate>
            <div>
              <label className="label" htmlFor="fp-email">Email</label>
              <input
                id="fp-email" type="email" className="input"
                placeholder="your@live.gctu.edu.gh"
                value={email} onChange={(e) => { setEmail(e.target.value); setErrors({}) }}
                autoComplete="email"
              />
              {errors.email && <p className="error-text">{errors.email}</p>}
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Sending…' : 'Send Reset Code'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <Link to="/login" className="text-sm text-slate-500 hover:text-slate-700
                                         dark:text-slate-400 dark:hover:text-slate-200">
              ← Back to login
            </Link>
          </div>
        </>
      ) : (
        <>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
            Reset your password
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
            Enter the code sent to{' '}
            <span className="font-medium text-slate-700 dark:text-slate-300">{email}</span>
          </p>

          <form onSubmit={handleStep2} className="space-y-4" noValidate>
            <div>
              <label className="label" htmlFor="fp-code">Reset code</label>
              <input
                id="fp-code" type="text" inputMode="numeric" maxLength={6}
                className="input tracking-[0.4em] text-center font-bold text-xl"
                placeholder="000000"
                value={code}
                onChange={(e) => { setCode(e.target.value.replace(/\D/g, '')); setErrors({}) }}
              />
              {errors.code && <p className="error-text">{errors.code}</p>}
            </div>

            <div>
              <label className="label" htmlFor="fp-new-pass">New password</label>
              <input
                id="fp-new-pass" type="password" className="input"
                placeholder="At least 8 characters"
                value={newPassword}
                onChange={(e) => { setNewPassword(e.target.value); setErrors({}) }}
                autoComplete="new-password"
              />
              {errors.newPassword && <p className="error-text">{errors.newPassword}</p>}
            </div>

            <div>
              <label className="label" htmlFor="fp-confirm-pass">Confirm new password</label>
              <input
                id="fp-confirm-pass" type="password" className="input"
                placeholder="Repeat new password"
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); setErrors({}) }}
                autoComplete="new-password"
              />
              {errors.confirmPassword && <p className="error-text">{errors.confirmPassword}</p>}
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Resetting…' : 'Reset Password'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              type="button"
              className="text-sm text-slate-500 hover:text-slate-700
                         dark:text-slate-400 dark:hover:text-slate-200"
              onClick={() => setStep(1)}
            >
              ← Back
            </button>
          </div>
        </>
      )}
    </AuthLayout>
  )
}
