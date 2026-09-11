import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import AuthLayout from '../components/AuthLayout'
import { authService } from '../services/authService'

export default function SignupPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [errors, setErrors]   = useState({})

  const [form, setForm] = useState({
    full_name: '',
    username: '',
    email: '',
    student_id: '',
    password: '',
    confirm_password: '',
    agree_to_guidelines: false,
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const errs = {}
    if (!form.full_name.trim()) errs.full_name = 'Full name is required'
    if (!form.username.trim()) errs.username = 'Username is required'
    if (form.username.length < 3) errs.username = 'Username must be at least 3 characters'
    if (!form.email.trim()) errs.email = 'Email is required'
    if (!form.email.toLowerCase().endsWith('@live.gctu.edu.gh'))
      errs.email = 'Please use your GCTU student email (@live.gctu.edu.gh)'
    if (!form.password) errs.password = 'Password is required'
    if (form.password.length < 8) errs.password = 'Password must be at least 8 characters'
    if (form.password !== form.confirm_password) errs.confirm_password = 'Passwords do not match'
    if (!form.agree_to_guidelines) errs.agree_to_guidelines = 'You must agree to the community guidelines'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }

    setLoading(true)
    try {
      await authService.register({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        student_id: form.student_id.trim() || undefined,
        password: form.password,
        confirm_password: form.confirm_password,
        agree_to_guidelines: form.agree_to_guidelines,
      })

      toast.success('Account created! Check your email for the verification code.')
      navigate('/verify-email', { state: { email: form.email.trim() } })
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        if (detail.toLowerCase().includes('email')) setErrors({ email: detail })
        else if (detail.toLowerCase().includes('username')) setErrors({ username: detail })
        else toast.error(detail)
      } else if (Array.isArray(detail)) {
        const fieldErrors = {}
        detail.forEach((d) => {
          const field = d.loc?.[d.loc.length - 1]
          if (field) fieldErrors[field] = d.msg.replace('Value error, ', '')
        })
        setErrors(fieldErrors)
      } else {
        toast.error('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
        Create your account
      </h1>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
        Already have one?{' '}
        <Link to="/login" className="text-brand-600 hover:underline font-medium dark:text-brand-400">
          Log in
        </Link>
      </p>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Full name */}
        <div>
          <label className="label" htmlFor="full_name">Full name</label>
          <input
            id="full_name" name="full_name" type="text"
            className="input" placeholder="Kwame Mensah"
            value={form.full_name} onChange={handleChange}
            autoComplete="name"
          />
          {errors.full_name && <p className="error-text">{errors.full_name}</p>}
        </div>

        {/* Username */}
        <div>
          <label className="label" htmlFor="username">Username</label>
          <input
            id="username" name="username" type="text"
            className="input" placeholder="kwame_m"
            value={form.username} onChange={handleChange}
            autoComplete="username"
          />
          {errors.username && <p className="error-text">{errors.username}</p>}
        </div>

        {/* University email */}
        <div>
          <label className="label" htmlFor="email">GCTU student email</label>
          <input
            id="email" name="email" type="email"
            className="input" placeholder="s0000000@live.gctu.edu.gh"
            value={form.email} onChange={handleChange}
            autoComplete="email"
          />
          {errors.email && <p className="error-text">{errors.email}</p>}
        </div>

        {/* Student ID (optional) */}
        <div>
          <label className="label" htmlFor="student_id">
            Student ID <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <input
            id="student_id" name="student_id" type="text"
            className="input" placeholder="GCTU/CS/21/0001"
            value={form.student_id} onChange={handleChange}
          />
        </div>

        {/* Password */}
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input
            id="password" name="password" type="password"
            className="input" placeholder="At least 8 characters"
            value={form.password} onChange={handleChange}
            autoComplete="new-password"
          />
          {errors.password && <p className="error-text">{errors.password}</p>}
        </div>

        {/* Confirm password */}
        <div>
          <label className="label" htmlFor="confirm_password">Confirm password</label>
          <input
            id="confirm_password" name="confirm_password" type="password"
            className="input" placeholder="Repeat your password"
            value={form.confirm_password} onChange={handleChange}
            autoComplete="new-password"
          />
          {errors.confirm_password && <p className="error-text">{errors.confirm_password}</p>}
        </div>

        {/* Guidelines checkbox */}
        <div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox" name="agree_to_guidelines"
              className="mt-0.5 w-4 h-4 rounded border-slate-300 text-brand-600
                         focus:ring-brand-500 cursor-pointer"
              checked={form.agree_to_guidelines} onChange={handleChange}
            />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              I agree to FAiND&apos;s{' '}
              <span className="text-brand-600 dark:text-brand-400 cursor-pointer hover:underline">
                community guidelines
              </span>
            </span>
          </label>
          {errors.agree_to_guidelines && (
            <p className="error-text">{errors.agree_to_guidelines}</p>
          )}
        </div>

        <button
          type="submit" className="btn-primary w-full mt-2" disabled={loading}
        >
          {loading ? 'Creating account…' : 'Create Account'}
        </button>
      </form>
    </AuthLayout>
  )
}
