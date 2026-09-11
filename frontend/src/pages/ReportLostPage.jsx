/**
 * Feature C — Report Lost Item
 */
import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import ImageUploadSlot from '../components/ImageUploadSlot'
import {
  createLostItem,
  uploadImageToCloudinary,
  findRecentLostItemMatch,
  isAmbiguousSubmitError,
} from '../services/itemService'
import { invalidateAfterItemCreate } from '../utils/queryCache'
import { useCampusZones } from '../hooks/useCampusZones'
import CategoryPicker from '../components/CategoryPicker'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

function Field({ label, hint, required, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {hint && <p className="text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
      {children}
    </div>
  )
}

export default function ReportLostPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [category, setCategory] = useState('')
  const [publicDesc, setPublicDesc] = useState('')
  const [locationId, setLocationId] = useState('')
  const [dateLost, setDateLost] = useState('')
  const [timeLost, setTimeLost] = useState('')
  const [images, setImages] = useState([null, null])
  const [uploadingIdx, setUploadingIdx] = useState(null)

  const todayMax = useMemo(() => new Date().toISOString().split('T')[0], [])
  const { zones, zonesLoading } = useCampusZones()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const SUBMIT_COOLDOWN_MS = 10_000

  const submitMutation = useMutation({
    mutationFn: createLostItem,
  })

  function scheduleSubmitCooldown() {
    setTimeout(release, SUBMIT_COOLDOWN_MS)
  }

  function formatApiError(err) {
    const detail = err?.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(', ')
    }
    if (err?.code === 'ECONNABORTED') {
      return 'The request timed out. Checking whether your item was saved…'
    }
    if (!err?.response) {
      return 'Network error. Checking whether your item was saved…'
    }
    return 'Failed to submit report. Please try again.'
  }

  function handleLostItemSuccess(data) {
    invalidateAfterItemCreate(queryClient, { type: 'lost' })
    const warnings = Array.isArray(data?.warnings) ? data.warnings : []
    warnings.forEach((w) => toast(w, { icon: '⚠️', duration: 6000 }))
    if (data?.already_submitted) {
      toast.success(data.message || 'Your item was already submitted successfully')
    } else {
      toast.success('Lost item reported successfully!')
    }
    navigate('/dashboard')
  }

  async function tryRecoverExistingLostItem(payload, locationLabel) {
    try {
      return await findRecentLostItemMatch({
        category: payload.category,
        location_label: locationLabel,
        public_description: payload.public_description,
      })
    } catch {
      return null
    }
  }

  async function handleImageSelect(file, idx) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) {
      toast.error('Only JPEG, PNG, and WEBP images are accepted')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be 5 MB or smaller')
      return
    }
    setUploadingIdx(idx)
    setImages((prev) => {
      const next = [...prev]
      next[idx] = { url: null }
      return next
    })
    try {
      const url = await uploadImageToCloudinary(file)
      setImages((prev) => {
        const next = [...prev]
        next[idx] = { url }
        return next
      })
    } catch (err) {
      toast.error(err.message || 'Image upload failed')
      setImages((prev) => {
        const next = [...prev]
        next[idx] = null
        return next
      })
    } finally {
      setUploadingIdx(null)
    }
  }

  function handleImageRemove(idx) {
    setImages((prev) => {
      const next = [...prev]
      next[idx] = null
      return next
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return

    if (!category) {
      release()
      return toast.error('Please select a category')
    }
    if (!publicDesc.trim()) {
      release()
      return toast.error('Public description is required')
    }
    if (!dateLost) {
      release()
      return toast.error('Date lost is required')
    }
    if (uploadingIdx !== null) {
      release()
      return toast.error('Please wait for the image to finish uploading')
    }

    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)
    const dateOccurred = timeLost
      ? `${dateLost}T${timeLost}:00`
      : `${dateLost}T00:00:00`

    const locationLabel = locationId
      ? (zones.find((z) => z.id === locationId)?.name || 'Unknown Location')
      : 'Unknown Location'

    const payload = {
      category,
      public_description: publicDesc.trim(),
      location_id: locationId || null,
      date_occurred: dateOccurred,
      image_urls: imageUrls,
    }

    try {
      const existing = await tryRecoverExistingLostItem(payload, locationLabel)
      if (existing) {
        handleLostItemSuccess({
          already_submitted: true,
          message: 'Your item was already submitted successfully',
        })
        return
      }

      const data = await submitMutation.mutateAsync(payload)
      handleLostItemSuccess(data)
    } catch (err) {
      if (isAmbiguousSubmitError(err)) {
        const recovered = await tryRecoverExistingLostItem(payload, locationLabel)
        if (recovered) {
          handleLostItemSuccess({
            already_submitted: true,
            message: 'Your item was already submitted successfully',
          })
          return
        }
      }
      toast.error(formatApiError(err))
    } finally {
      scheduleSubmitCooldown()
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />

      <div className="max-w-2xl mx-auto px-4 py-10 max-md:py-5 overflow-x-hidden">
        <div className="mb-8 max-md:mb-5">
          <h1 className="text-2xl max-md:text-xl font-bold text-slate-900 dark:text-white">
            Report a Lost Item
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Describe what you lost so the campus community can help you find it.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-7 max-md:gap-5">
          <div className="glass p-6 max-md:p-4 relative z-[1] overflow-visible">
            <h2 className="section-heading mb-5">Item Details</h2>
            <div className="flex flex-col gap-5">
              <Field label="Category" required hint="Choose the category that best matches your item.">
                <CategoryPicker value={category} onChange={setCategory} />
              </Field>

              <Field
                label="Public Description"
                hint="Describe what you lost. This is visible to everyone."
                required
              >
                <textarea
                  value={publicDesc}
                  onChange={(e) => setPublicDesc(e.target.value)}
                  rows={3}
                  maxLength={1000}
                  placeholder="e.g. Black Samsung Galaxy S23 with a cracked screen protector"
                  className="input-field resize-none"
                  required
                />
                <span className="text-xs text-slate-400 text-right">{publicDesc.length}/1000</span>
              </Field>
            </div>
          </div>

          <div className="glass p-6 max-md:p-4">
            <h2 className="section-heading mb-5">Where & When</h2>
            <div className="flex flex-col gap-5">
              <Field label="Campus Location">
                {zonesLoading ? (
                  <div className="input-field text-slate-400">Loading zones…</div>
                ) : (
                  <select
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Not sure / multiple locations</option>
                    {zones.map((z) => (
                      <option key={z.id} value={z.id}>{z.name}</option>
                    ))}
                  </select>
                )}
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label="Date Lost" required>
                  <input
                    type="date"
                    value={dateLost}
                    max={todayMax}
                    onChange={(e) => setDateLost(e.target.value)}
                    className="input-field"
                    required
                  />
                </Field>
                <Field label="Approximate Time">
                  <input
                    type="time"
                    value={timeLost}
                    onChange={(e) => setTimeLost(e.target.value)}
                    className="input-field"
                  />
                </Field>
              </div>
            </div>
          </div>

          <div className="glass p-6 max-md:p-4">
            <h2 className="section-heading mb-1">Photos</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
              Optional — up to 2 photos. JPEG, PNG, or WEBP, max 5 MB each.
            </p>
            <div className="flex gap-4">
              {images.map((img, idx) => (
                <ImageUploadSlot
                  key={idx}
                  index={idx}
                  imageUrl={img?.url || null}
                  uploading={uploadingIdx === idx}
                  onSelect={(file) => handleImageSelect(file, idx)}
                  onRemove={() => handleImageRemove(idx)}
                />
              ))}
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="btn-secondary"
              disabled={isSubmitting || submitMutation.isPending}
            >
              Cancel
            </button>
            <SubmitButton
              loading={isSubmitting || submitMutation.isPending}
              disabled={uploadingIdx !== null}
              className="btn-primary min-w-[140px] mobile-form-submit md:w-auto"
              loadingLabel="Submitting…"
            >
              Submit Report
            </SubmitButton>
          </div>
        </form>
      </div>
    </div>
  )
}
