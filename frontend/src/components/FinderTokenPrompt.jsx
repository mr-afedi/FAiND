/**
 * Section 9.3 — post drop-off token registration prompt for anonymous finders.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  claimEscrowLogin,
  claimEscrowRegister,
  discardEscrow,
} from '../services/tokenService'
import { getEscrowToken, saveEscrowToken, clearEscrowToken } from '../utils/tokenEscrow'
import { setAccessToken } from '../services/api'
import { authService } from '../services/authService'
import { useAuth } from '../context/AuthContext'

export default function FinderTokenPrompt({
  tokenEscrow,
  onDismiss,
  onClaimed,
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { afterEmailVerification } = useAuth()
  const [mode, setMode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    full_name: '',
    username: '',
    email: '',
    student_id: '',
    password: '',
    confirm_password: '',
    agree_to_guidelines: false,
    login_email: '',
    login_password: '',
  })

  const total = tokenEscrow?.pending_total || 0
  const escrowToken = tokenEscrow?.escrow_token || getEscrowToken()

  if (!tokenEscrow?.show_registration_prompt || total <= 0) {
    return null
  }

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  async function handleSkip() {
    if (escrowToken) saveEscrowToken(escrowToken)
    toast.success('Tokens saved — claim them within 7 days by signing in on this device.')
    onDismiss?.()
  }

  async function handleDecline() {
    if (!escrowToken) {
      onDismiss?.()
      return
    }
    setLoading(true)
    try {
      await discardEscrow(escrowToken)
      clearEscrowToken()
      toast.success('No problem — tokens discarded.')
      onDismiss?.()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not discard tokens')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e) {
    e.preventDefault()
    if (!escrowToken) return toast.error('Missing escrow token — try refreshing the page.')
    setLoading(true)
    try {
      const data = await claimEscrowRegister({
        escrowToken,
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        student_id: form.student_id.trim() || undefined,
        password: form.password,
        confirm_password: form.confirm_password,
        agree_to_guidelines: form.agree_to_guidelines,
      })
      const email = form.email.trim()
      sessionStorage.setItem('faind_verify_email', email)
      clearEscrowToken()
      toast.success(data.message)
      onClaimed?.()
      navigate('/verify-email', {
        replace: true,
        state: { email, tokensClaimed: data.tokens_claimed },
      })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleLogin(e) {
    e.preventDefault()
    if (!escrowToken) return toast.error('Missing escrow token — try refreshing the page.')
    setLoading(true)
    try {
      const data = await claimEscrowLogin({
        escrowToken,
        email: form.login_email.trim(),
        password: form.login_password,
      })
      setAccessToken(data.access_token)
      const me = await authService.getMe()
      afterEmailVerification(data.access_token, me)
      clearEscrowToken()
      toast.success(data.message)
      onClaimed?.()
      await queryClient.invalidateQueries({ queryKey: ['my-tokens'] })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail || 'Could not claim tokens'
      if (status === 403 && String(detail).toLowerCase().includes('verify')) {
        const email = form.login_email.trim()
        sessionStorage.setItem('faind_verify_email', email)
        navigate('/verify-email', { replace: true, state: { email, fromLogin: true } })
      } else {
        toast.error(detail)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass p-6 border border-brand-200/70 dark:border-brand-800/50 space-y-4">
      <div>
        <p className="text-lg font-bold text-slate-900 dark:text-white">
          🎉 You just helped someone on campus!
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">
          You&apos;ve earned <strong>{total} tokens</strong>. Create a free account to claim
          your tokens and receive appreciation from the item&apos;s owner.
        </p>
      </div>

      {!mode && (
        <div className="flex flex-col sm:flex-row gap-2">
          <button
            type="button"
            className="btn-primary text-sm"
            disabled={loading}
            onClick={() => setMode('register')}
          >
            Claim my tokens
          </button>
          <button
            type="button"
            className="btn-secondary text-sm"
            disabled={loading}
            onClick={handleSkip}
          >
            Skip for now
          </button>
          <button
            type="button"
            className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 px-2"
            disabled={loading}
            onClick={handleDecline}
          >
            I don&apos;t want tokens
          </button>
        </div>
      )}

      {mode === 'register' && (
        <form onSubmit={handleRegister} className="space-y-3">
          <p className="text-xs text-slate-500">Quick signup — tokens credited immediately.</p>
          <input name="full_name" value={form.full_name} onChange={handleChange} placeholder="Full name" className="input-field" required />
          <input name="username" value={form.username} onChange={handleChange} placeholder="Username" className="input-field" required />
          <input name="email" type="email" value={form.email} onChange={handleChange} placeholder="GCTU email (@live.gctu.edu.gh)" className="input-field" required />
          <input name="student_id" value={form.student_id} onChange={handleChange} placeholder="Student ID (optional)" className="input-field" />
          <input name="password" type="password" value={form.password} onChange={handleChange} placeholder="Password" className="input-field" required />
          <input name="confirm_password" type="password" value={form.confirm_password} onChange={handleChange} placeholder="Confirm password" className="input-field" required />
          <label className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
            <input type="checkbox" name="agree_to_guidelines" checked={form.agree_to_guidelines} onChange={handleChange} className="mt-0.5" />
            I agree to the community guidelines
          </label>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm" disabled={loading}>
              {loading ? 'Creating account…' : 'Create account & claim tokens'}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={() => setMode('login')}>
              Already have an account?
            </button>
          </div>
        </form>
      )}

      {mode === 'login' && (
        <form onSubmit={handleLogin} className="space-y-3">
          <input name="login_email" type="email" value={form.login_email} onChange={handleChange} placeholder="Email" className="input-field" required />
          <input name="login_password" type="password" value={form.login_password} onChange={handleChange} placeholder="Password" className="input-field" required />
          <div className="flex gap-2">
            <button type="submit" className="btn-primary text-sm" disabled={loading}>
              {loading ? 'Claiming…' : 'Log in & claim tokens'}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={() => setMode('register')}>
              New here?
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
