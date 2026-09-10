/**
 * Supervisor login — email + password (Section 15.2).
 */
import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  supervisorLogin,
  getSupervisorMe,
  setSupervisorAccessToken,
} from '../services/supervisorService'
import { useSupervisorAuth } from '../context/SupervisorAuthContext'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

export default function SupervisorLoginPage() {
  const navigate = useNavigate()
  const { completeLogin, isSupervisorAuthenticated, loading } = useSupervisorAuth()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (!loading && isSupervisorAuthenticated) {
      navigate('/supervisor/dashboard', { replace: true })
    }
  }, [loading, isSupervisorAuthenticated, navigate])

  if (loading || isSupervisorAuthenticated) {
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
      const data = await supervisorLogin(email.trim(), password)
      setSupervisorAccessToken(data.access_token)
      const profile = await getSupervisorMe()
      completeLogin(data.access_token, profile)
      toast.success('Signed in')
      navigate('/supervisor/dashboard', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Sign-in failed')
    } finally {
      release()
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="glass w-full max-w-md p-8">
        <h1 className="text-xl font-bold text-slate-100 mb-1">FAiND Supervisor</h1>
        <p className="text-sm text-slate-400 mb-6">Drop point group oversight</p>
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
        <p className="text-xs text-slate-500 mt-6 text-center">
          <Link to="/" className="hover:text-slate-300">← Back to FAiND</Link>
        </p>
      </div>
    </div>
  )
}
