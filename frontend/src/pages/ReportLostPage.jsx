/**
 * Feature C — Report Lost Item (Section 6, Section 30.5, Section 30.6)
 *
 * Fields:
 *   - Category dropdown
 *   - Public description (visible to all)
 *   - Private description (encrypted at rest, used only for verification)
 *   - Campus location (dropdown from /items/campus-zones)
 *   - Date and time lost
 *   - Images (optional, max 2, Cloudinary upload)
 *   V4.2: hidden verification Q&A are on found items only (finder sets them).
 */
import { useState, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import {
  createLostItem,
  uploadImageToCloudinary,
} from '../services/itemService'
import { invalidateAfterItemCreate } from '../utils/queryCache'
import { useCampusZones } from '../hooks/useCampusZones'
import { X } from '../components/icons'
import CategoryPicker from '../components/CategoryPicker'

// ── Reusable form field wrapper ───────────────────────────────────────────────

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

// ── Image preview / upload row ────────────────────────────────────────────────

function ImageUploadSlot({ index, preview, uploading, onSelect, onRemove }) {
  const inputRef = useRef(null)
  return (
    <div className="relative w-28 h-28 rounded-xl border-2 border-dashed
                    border-slate-300 dark:border-slate-600 overflow-hidden
                    flex items-center justify-center cursor-pointer
                    hover:border-brand-400 transition-colors"
         onClick={() => !preview && inputRef.current?.click()}>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => e.target.files[0] && onSelect(e.target.files[0])}
      />
      {preview ? (
        <>
          <img src={preview} alt={`image ${index + 1}`} className="w-full h-full object-cover" />
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRemove() }}
            className="absolute top-1 right-1 bg-red-600 text-white text-xs
                       rounded-full w-5 h-5 flex items-center justify-center
                       hover:bg-red-700 transition-colors"
          >
            <X className="w-3 h-3" aria-hidden />
          </button>
        </>
      ) : uploading ? (
        <div className="flex flex-col items-center gap-1 text-slate-400">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">Uploading…</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1 text-slate-400 select-none">
          <span className="text-2xl">+</span>
          <span className="text-xs">Add photo</span>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReportLostPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // form state
  const [category, setCategory]             = useState('')
  const [publicDesc, setPublicDesc]         = useState('')
  const [privateDesc, setPrivateDesc]       = useState('')
  const [locationId, setLocationId]         = useState('')
  const [dateLost, setDateLost]             = useState('')
  const [timeLost, setTimeLost]             = useState('')
  const [images, setImages]                 = useState([null, null])        // null | { file, preview, url }
  const [uploadingIdx, setUploadingIdx]     = useState(null)

  const todayMax = useMemo(() => new Date().toISOString().split('T')[0], [])

  const { zones, zonesLoading } = useCampusZones()

  // Submit mutation
  // Guard against double-submit (e.g. rapid double-click or Enter key bounce)
  const submittingRef = useRef(false)

  const { mutate: submit, isPending } = useMutation({
    mutationFn: createLostItem,
    onSuccess: () => {
      invalidateAfterItemCreate(queryClient, { type: 'lost' })
      toast.success('Lost item reported successfully!')
      navigate('/dashboard')
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Failed to submit report. Please try again.'
      toast.error(msg)
    },
    onSettled: () => {
      submittingRef.current = false
    },
  })

  // ── Image upload handler ────────────────────────────────────────────────────
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
    // local preview immediately
    const preview = URL.createObjectURL(file)
    setImages((prev) => {
      const next = [...prev]
      next[idx] = { file, preview, url: null }
      return next
    })
    setUploadingIdx(idx)
    try {
      const url = await uploadImageToCloudinary(file)
      setImages((prev) => {
        const next = [...prev]
        next[idx] = { file, preview, url }
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
      if (next[idx]?.preview) URL.revokeObjectURL(next[idx].preview)
      next[idx] = null
      return next
    })
  }

  // ── Submit ──────────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault()

    // Hard guard — prevents double-submit regardless of button state
    if (submittingRef.current || isPending) return
    submittingRef.current = true

    // client-side validation
    if (!category)          { submittingRef.current = false; return toast.error('Please select a category') }
    if (!publicDesc.trim()) { submittingRef.current = false; return toast.error('Public description is required') }
    if (!privateDesc.trim()){ submittingRef.current = false; return toast.error('Private description is required') }
    if (!dateLost)          { submittingRef.current = false; return toast.error('Date lost is required') }

    // check any upload still in progress
    if (uploadingIdx !== null) {
      submittingRef.current = false
      return toast.error('Please wait for the image to finish uploading')
    }

    // collect uploaded image URLs (skip nulls and images still uploading)
    const imageUrls = images
      .filter((img) => img?.url)
      .map((img) => img.url)

    // build datetime from date + time inputs
    const dateOccurred = timeLost
      ? `${dateLost}T${timeLost}:00`
      : `${dateLost}T00:00:00`

    submit({
      category,
      public_description: publicDesc.trim(),
      private_description: privateDesc.trim(),
      location_id: locationId || null,
      date_occurred: dateOccurred,
      image_urls: imageUrls,
    })
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />

      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Report a Lost Item
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Fill in the details below. Private fields are encrypted and only used to verify ownership — they are never shown to anyone.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-7">

          {/* ── Item details ── */}
          <div className="glass p-6 relative z-[1] overflow-visible">
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

              <Field
                label="Private Description"
                hint="Include specific details only the real owner would know. This is encrypted and never shown to anyone — it's used only to verify your ownership."
                required
              >
                <textarea
                  value={privateDesc}
                  onChange={(e) => setPrivateDesc(e.target.value)}
                  rows={3}
                  maxLength={1000}
                  placeholder="e.g. Has a small crack on the back bottom-right corner, wallpaper is a photo of my dog"
                  className="input-field resize-none"
                  required
                />
                <span className="text-xs text-slate-400 text-right">{privateDesc.length}/1000</span>
              </Field>
            </div>
          </div>

          {/* ── Location & Date ── */}
          <div className="glass p-6">
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

          {/* ── Images ── */}
          <div className="glass p-6">
            <h2 className="section-heading mb-1">Photos</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
              Optional — up to 2 photos. JPEG, PNG, or WEBP, max 5 MB each.
            </p>
            <div className="flex gap-4">
              {images.map((img, idx) => (
                <ImageUploadSlot
                  key={idx}
                  index={idx}
                  preview={img?.preview || null}
                  uploading={uploadingIdx === idx}
                  onSelect={(file) => handleImageSelect(file, idx)}
                  onRemove={() => handleImageRemove(idx)}
                />
              ))}
            </div>
          </div>

          {/* ── Actions ── */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="btn-secondary"
              disabled={isPending}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || uploadingIdx !== null}
              className="btn-primary min-w-[140px]"
            >
              {isPending ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Submitting…
                </span>
              ) : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
