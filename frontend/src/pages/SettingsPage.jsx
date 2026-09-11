import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { userService } from '../services/userService'
import { uploadImageToCloudinary } from '../services/itemService'
import { useAuth } from '../context/AuthContext'
import NavBar from '../components/NavBar'
import { usePushNotifications } from '../hooks/usePushNotifications'
import { invalidateAfterProfileUpdate } from '../utils/queryCache'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

// ── Reusable toggle component ─────────────────────────────────────────────────

function Toggle({ on, onChange, label, description }) {
  return (
    <div className="flex items-center justify-between py-3
                    border-b border-slate-100 dark:border-slate-800 last:border-0">
      <div>
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</p>
        {description && (
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{description}</p>
        )}
      </div>
      <button
        role="switch"
        aria-checked={on}
        onClick={() => onChange(!on)}
        className={`toggle ${on ? 'on' : ''}`}
      >
        <span className="toggle-thumb" />
      </button>
    </div>
  )
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children }) {
  return (
    <div className="glass p-6 mb-4">
      <h2 className="section-heading mb-4">{title}</h2>
      {children}
    </div>
  )
}

// ── Field row ─────────────────────────────────────────────────────────────────

function FieldRow({ label, children, error }) {
  return (
    <div className="mb-4">
      <label className="label">{label}</label>
      {children}
      {error && <p className="error-text">{error}</p>}
    </div>
  )
}

// ── Delete account dialog ─────────────────────────────────────────────────────

function DeleteDialog({ onClose, onConfirm, loading }) {
  const [password, setPassword] = useState('')
  const [typed, setTyped] = useState('')

  const ready = typed.toUpperCase() === 'DELETE' && password.length > 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4
                    bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="glass max-w-md w-full p-6 animate-slide-up">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30
                          flex items-center justify-center flex-shrink-0 text-red-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 dark:text-slate-100">Delete Account</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              This is permanent and irreversible. All your data will be deleted.
            </p>
          </div>
        </div>

        <div className="mb-3">
          <label className="label">Current password</label>
          <input
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
          />
        </div>

        <div className="mb-5">
          <label className="label">
            Type <span className="font-mono font-bold text-red-600">DELETE</span> to confirm
          </label>
          <input
            type="text"
            className="input"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="DELETE"
          />
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="btn-secondary flex-1" disabled={loading}>
            Cancel
          </button>
          <button
            onClick={() => onConfirm(password)}
            disabled={!ready || loading}
            className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-2.5
                       rounded-xl bg-red-600 text-white font-medium text-sm
                       transition-all duration-200 hover:bg-red-700 active:scale-95
                       disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : 'Delete Forever'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { logout } = useAuth()
  const {
    supported: pushSupported,
    permissionState,
    isSubscribed,
    requestPermissionAndSubscribe,
    unsubscribe: pushUnsubscribe,
  } = usePushNotifications()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Profile form state
  const [profileForm, setProfileForm] = useState(null)
  const [profileErrors, setProfileErrors] = useState({})
  const [photoUploading, setPhotoUploading] = useState(false)
  const photoInputRef = useRef(null)

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const profileLock = useSubmitLock()
  const passwordLock = useSubmitLock()
  const [passwordErrors, setPasswordErrors] = useState({})
  const [showPasswords, setShowPasswords] = useState(false)

  // ── Load profile ──
  const { data: profile, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: userService.getMe,
    onSuccess: (data) => {
      if (!profileForm) {
        setProfileForm({
          full_name: data.full_name,
          student_id: data.student_id || '',
          profile_photo_url: data.profile_photo_url || '',
        })
      }
    },
  })

  // Initialise profileForm when profile loads (handles the case where onSuccess isn't called)
  const currentProfile = profile
  if (currentProfile && profileForm === null) {
    setProfileForm({
      full_name: currentProfile.full_name,
      student_id: currentProfile.student_id || '',
      profile_photo_url: currentProfile.profile_photo_url || '',
    })
  }

  // ── Mutations ──
  const updateProfileMutation = useMutation({
    mutationFn: userService.updateProfile,
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], data)
      invalidateAfterProfileUpdate(queryClient)
      toast.success('Profile updated.')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to update profile.')
    },
    onSettled: () => profileLock.release(),
  })

  const changePasswordMutation = useMutation({
    mutationFn: ({ current, next, confirm }) =>
      userService.changePassword(current, next, confirm),
    onSuccess: () => {
      toast.success('Password changed. Please log in again.')
      logout()
    },
    onError: (err) => {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        if (detail.toLowerCase().includes('incorrect')) {
          setPasswordErrors({ current_password: detail })
        } else {
          toast.error(detail)
        }
      } else {
        toast.error('Failed to change password.')
      }
    },
    onSettled: () => passwordLock.release(),
  })

  const updateSettingsMutation = useMutation({
    mutationFn: userService.updateSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], data)
      invalidateAfterProfileUpdate(queryClient)
    },
    onError: () => toast.error('Failed to save setting.'),
  })

  const deleteAccountMutation = useMutation({
    mutationFn: userService.deleteAccount,
    onSuccess: () => {
      toast.success('Account deleted.')
      logout()
      navigate('/')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to delete account.')
    },
  })

  // ── Photo upload handler ──────────────────────────────────────────────────
  async function handlePhotoSelect(e) {
    const file = e.target.files?.[0]
    if (!file) return
    // reset so same file can be re-selected if needed
    e.target.value = ''

    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) {
      return toast.error('Only JPEG, PNG, and WEBP images are accepted')
    }
    if (file.size > 5 * 1024 * 1024) {
      return toast.error('Photo must be 5 MB or smaller')
    }

    setPhotoUploading(true)
    try {
      const url = await uploadImageToCloudinary(file)
      // Immediately save to profile
      await userService.updateProfile({ profile_photo_url: url })
      queryClient.setQueryData(['me'], (old) => old ? { ...old, profile_photo_url: url } : old)
      invalidateAfterProfileUpdate(queryClient)
      // Also keep the local form in sync
      setProfileForm((f) => f ? { ...f, profile_photo_url: url } : f)
      toast.success('Profile photo updated!')
    } catch (err) {
      toast.error(err.message || 'Photo upload failed')
    } finally {
      setPhotoUploading(false)
    }
  }

  async function handlePhotoRemove() {
    setPhotoUploading(true)
    try {
      await userService.updateProfile({ profile_photo_url: null })
      queryClient.setQueryData(['me'], (old) => old ? { ...old, profile_photo_url: null } : old)
      invalidateAfterProfileUpdate(queryClient)
      setProfileForm((f) => f ? { ...f, profile_photo_url: '' } : f)
      toast.success('Profile photo removed')
    } catch (err) {
      toast.error('Failed to remove photo')
    } finally {
      setPhotoUploading(false)
    }
  }

  // ── Handlers ──
  function handleProfileSubmit(e) {
    e.preventDefault()
    if (!profileLock.tryAcquire()) return
    setProfileErrors({})
    const errors = {}
    if (!profileForm.full_name?.trim()) errors.full_name = 'Name is required.'
    else if (profileForm.full_name.trim().length < 2) errors.full_name = 'Name too short.'
    if (Object.keys(errors).length) {
      profileLock.release()
      setProfileErrors(errors)
      return
    }
    updateProfileMutation.mutate({
      full_name: profileForm.full_name.trim(),
      student_id: profileForm.student_id.trim() || null,
    })
  }

  function handlePasswordSubmit(e) {
    e.preventDefault()
    if (!passwordLock.tryAcquire()) return
    setPasswordErrors({})
    const errors = {}
    if (!passwordForm.current_password) errors.current_password = 'Required.'
    if (passwordForm.new_password.length < 8) errors.new_password = 'At least 8 characters.'
    if (passwordForm.new_password !== passwordForm.confirm_password)
      errors.confirm_password = 'Passwords do not match.'
    if (Object.keys(errors).length) {
      passwordLock.release()
      setPasswordErrors(errors)
      return
    }
    changePasswordMutation.mutate({
      current: passwordForm.current_password,
      next: passwordForm.new_password,
      confirm: passwordForm.confirm_password,
    })
  }

  async function handleToggle(key, value) {
    if (key === 'push_notifications_enabled') {
      if (value) {
        if (!pushSupported) {
          toast.error('Your browser does not support push notifications.')
          return
        }
        if (permissionState === 'denied') {
          toast.error(
            'Push notifications are blocked. Please allow them in your browser settings.'
          )
          return
        }
        const ok = await requestPermissionAndSubscribe()
        if (!ok) return
        toast.success('Push notifications enabled.')
      } else {
        await pushUnsubscribe()
      }
    }
    updateSettingsMutation.mutate({ [key]: value })
  }

  if (isLoading || !profileForm) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 flex items-center justify-center min-h-[60vh]">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <NavBar />

      <div className="page-container py-8 max-w-2xl">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-6">Settings</h1>

        {/* ── Profile info ── */}
        <Section title="Profile Information">
          <form onSubmit={handleProfileSubmit}>
            <FieldRow label="Display Name" error={profileErrors.full_name}>
              <input
                type="text"
                className="input"
                value={profileForm.full_name}
                onChange={(e) => setProfileForm((f) => ({ ...f, full_name: e.target.value }))}
                placeholder="Your name"
              />
            </FieldRow>

            <FieldRow label="Student ID (optional)"
                      error={profileErrors.student_id}>
              <input
                type="text"
                className="input"
                value={profileForm.student_id}
                onChange={(e) => setProfileForm((f) => ({ ...f, student_id: e.target.value }))}
                placeholder="e.g. CS/0001/22"
              />
            </FieldRow>

            {/* ── Profile photo upload ── */}
            <FieldRow label="Profile Photo">
              <div className="flex items-center gap-4">
                {/* Avatar preview */}
                <div className="relative flex-shrink-0">
                  {profileForm?.profile_photo_url ? (
                    <img
                      src={profileForm.profile_photo_url}
                      alt="profile"
                      className="w-20 h-20 rounded-2xl object-cover border-2 border-slate-200 dark:border-slate-700"
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-2xl bg-brand-600 flex items-center justify-center
                                    text-white text-2xl font-bold border-2 border-slate-200 dark:border-slate-700">
                      {profile?.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase() || '?'}
                    </div>
                  )}
                  {photoUploading && (
                    <div className="absolute inset-0 rounded-2xl bg-black/50 flex items-center justify-center">
                      <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-2">
                  <input
                    ref={photoInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={handlePhotoSelect}
                  />
                  <button
                    type="button"
                    onClick={() => photoInputRef.current?.click()}
                    disabled={photoUploading}
                    className="btn-secondary text-xs py-1.5 px-4"
                  >
                    {photoUploading ? 'Uploading…' : profileForm?.profile_photo_url ? 'Change Photo' : 'Upload Photo'}
                  </button>
                  {profileForm?.profile_photo_url && (
                    <button
                      type="button"
                      onClick={handlePhotoRemove}
                      disabled={photoUploading}
                      className="text-xs text-red-500 hover:text-red-700 dark:text-red-400
                                 dark:hover:text-red-300 transition-colors disabled:opacity-50"
                    >
                      Remove photo
                    </button>
                  )}
                  <p className="text-xs text-slate-400">JPEG, PNG or WEBP · max 5 MB</p>
                </div>
              </div>
            </FieldRow>

            <SubmitButton
              loading={profileLock.isSubmitting || updateProfileMutation.isPending}
              className="btn-primary"
              loadingLabel="Saving…"
            >
              Save Changes
            </SubmitButton>
          </form>
        </Section>

        {/* ── Change password ── */}
        <Section title="Change Password">
          <form onSubmit={handlePasswordSubmit}>
            <FieldRow label="Current Password" error={passwordErrors.current_password}>
              <div className="relative">
                <input
                  type={showPasswords ? 'text' : 'password'}
                  className="input pr-10"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm((f) => ({ ...f, current_password: e.target.value }))}
                  placeholder="Current password"
                />
              </div>
            </FieldRow>

            <FieldRow label="New Password" error={passwordErrors.new_password}>
              <input
                type={showPasswords ? 'text' : 'password'}
                className="input"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                placeholder="Min 8 characters"
              />
            </FieldRow>

            <FieldRow label="Confirm New Password" error={passwordErrors.confirm_password}>
              <input
                type={showPasswords ? 'text' : 'password'}
                className="input"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, confirm_password: e.target.value }))}
                placeholder="Repeat new password"
              />
            </FieldRow>

            <div className="flex items-center gap-2 mb-4">
              <input
                id="show-pass"
                type="checkbox"
                className="rounded border-slate-300"
                checked={showPasswords}
                onChange={(e) => setShowPasswords(e.target.checked)}
              />
              <label htmlFor="show-pass" className="text-sm text-slate-600 dark:text-slate-400 cursor-pointer">
                Show passwords
              </label>
            </div>

            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
              Changing your password will sign you out of all devices.
            </p>

            <SubmitButton
              loading={passwordLock.isSubmitting || changePasswordMutation.isPending}
              className="btn-primary"
              loadingLabel="Changing…"
            >
              Change Password
            </SubmitButton>
          </form>
        </Section>

        {/* ── Notifications (Section 14.3) ── */}
        <Section title="Notifications">
          <Toggle
            on={(profile?.push_notifications_enabled && isSubscribed) ?? false}
            onChange={(v) => handleToggle('push_notifications_enabled', v)}
            label="Push Notifications"
            description={
              permissionState === 'denied'
                ? 'Blocked by browser — allow in browser settings then try again'
                : !pushSupported
                ? 'Not supported in this browser'
                : 'Get push alerts for matches, claims, and returns — even when the app is closed'
            }
          />
          <Toggle
            on={profile?.email_notifications_enabled ?? false}
            onChange={(v) => handleToggle('email_notifications_enabled', v)}
            label="Email Notifications"
            description="Coming soon — email summaries and alerts"
          />
        </Section>

        {/* ── Danger zone ── */}
        <div className="danger-zone">
          <h2 className="section-heading text-red-700 dark:text-red-400 mb-2">Danger Zone</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Deleting your account is permanent. All posts and matches will be removed.
          </p>
          <button
            onClick={() => setShowDeleteDialog(true)}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5
                       rounded-xl border border-red-300 dark:border-red-700
                       text-red-600 dark:text-red-400 font-medium text-sm
                       hover:bg-red-50 dark:hover:bg-red-900/20
                       transition-all duration-200 active:scale-95"
          >
            Delete Account
          </button>
        </div>
      </div>

      {showDeleteDialog && (
        <DeleteDialog
          onClose={() => setShowDeleteDialog(false)}
          onConfirm={(password) => deleteAccountMutation.mutate(password)}
          loading={deleteAccountMutation.isPending}
        />
      )}
    </div>
  )
}
