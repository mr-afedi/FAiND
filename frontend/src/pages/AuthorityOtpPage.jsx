/**
 * Authority email OTP step — reached from unified /login (Section 16.2).
 */
import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import {
  authorityVerifyOtp,
  getAuthorityMe,
  setAuthorityAccessToken,
  getAuthorityOtpSession,
  clearAuthorityOtpSession,
} from '../services/authorityService'
import { useAuthorityAuth } from '../context/AuthorityAuthContext'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

function formatVerifyError(err) {
  if (err.message && !err.response) return err.message
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(' ')
  }
  if (typeof detail === 'string') return detail
  return 'Invalid code'
}

export default function AuthorityOtpPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { completeLogin } = useAuthorityAuth()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const sessionToken = location.state?.sessionToken || getAuthorityOtpSession()

  const [otpCode, setOtpCode] = useState('')
  const [codeError, setCodeError] = useState('')

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

  async function handleOtp(e) {
    e.preventDefault()
    const code = otpCode.trim()
    if (!/^\d{6}$/.test(code)) {
      setCodeError('Enter the full 6-digit code (include any leading zeros).')
      return
    }
    setCodeError('')
    if (!tryAcquire()) return
    try {
      const data = await authorityVerifyOtp(sessionToken, code)
      setAuthorityAccessToken(data.access_token)
      const profile = await getAuthorityMe()
      completeLogin(data.access_token, profile)
      clearAuthorityOtpSession()
      toast.success(`Signed in as ${profile.drop_point_name}`)
      navigate('/authority/dashboard', { replace: true })
    } catch (err) {
      toast.error(formatVerifyError(err))
    } finally {
      release()
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Authority verification
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Enter the 6-digit code sent to your email.
      </p>

      <form onSubmit={handleOtp} className="space-y-4">
        <div>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            className="input text-center tracking-widest text-lg"
            value={otpCode}
            onChange={(e) => {
              setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))
              setCodeError('')
            }}
            required
            autoFocus
            aria-invalid={Boolean(codeError)}
          />
          {codeError && <p className="error-text mt-1">{codeError}</p>}
        </div>
        <SubmitButton loading={isSubmitting} className="btn-primary w-full">
          Verify & sign in
        </SubmitButton>
        <Link
          to="/login"
          className="btn-ghost w-full text-center block text-slate-500"
          onClick={() => clearAuthorityOtpSession()}
        >
          ← Back to login
        </Link>
      </form>
    </AuthLayout>
  )
}
