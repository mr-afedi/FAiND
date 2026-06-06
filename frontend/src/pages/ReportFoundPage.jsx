/**
 * Feature D — Report Found Item (Section 7, Section 30.5, Section 30.6)
 *
 * Key differences from Lost Item form:
 *   - At least ONE image is MANDATORY — submission blocked without it
 *   - NO private description
 *   - 2–3 hidden verification Q&A (finder sets, V4.2)
 *   - Initial status → FOUND (not OPEN)
 *   - Active period: 21 days
 */
import { useState, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import FinderVerificationQuestions from '../components/FinderVerificationQuestions'
import {
  createFoundItem,
  uploadImageToCloudinary,
} from '../services/itemService'
import { invalidateAfterItemCreate } from '../utils/queryCache'
import { useCampusZones, createInitialQuestions, newQuestion } from '../hooks/useCampusZones'
import { X, Camera, Plus } from '../components/icons'
import CategoryPicker from '../components/CategoryPicker'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

// ── Reusable field wrapper ────────────────────────────────────────────────────

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

// ── Image upload slot ─────────────────────────────────────────────────────────

function ImageUploadSlot({ index, preview, uploading, required, onSelect, onRemove }) {
  const inputRef = useRef(null)
  return (
    <div
      className={`relative w-28 h-28 rounded-xl border-2 border-dashed overflow-hidden
                  flex items-center justify-center cursor-pointer transition-colors
                  ${required && !preview && !uploading
                    ? 'border-red-400 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10'
                    : 'border-slate-300 dark:border-slate-600 hover:border-brand-400'
                  }`}
      onClick={() => !preview && inputRef.current?.click()}
    >
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
                       rounded-full w-5 h-5 flex items-center justify-center hover:bg-red-700"
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
        <div className="flex flex-col items-center gap-1 select-none
                        text-slate-400 dark:text-slate-500">
          {required ? (
            <Camera className="w-7 h-7" aria-hidden />
          ) : (
            <Plus className="w-7 h-7" aria-hidden />
          )}
          <span className="text-xs text-center leading-tight px-1">
            {required ? 'Required' : 'Add photo'}
          </span>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReportFoundPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [category, setCategory]         = useState('')
  const [description, setDescription]   = useState('')
  const [locationId, setLocationId]     = useState('')
  const [dateFound, setDateFound]       = useState('')
  const [timeFound, setTimeFound]       = useState('')
  const [images, setImages]             = useState([null, null])
  const [uploadingIdx, setUploadingIdx] = useState(null)
  const [questions, setQuestions]       = useState(() => createInitialQuestions(2))

  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const todayMax = useMemo(() => new Date().toISOString().split('T')[0], [])

  const { zones, zonesLoading } = useCampusZones()

  const { mutate: submit, isPending } = useMutation({
    mutationFn: createFoundItem,
    onSuccess: () => {
      invalidateAfterItemCreate(queryClient, { type: 'found' })
      toast.success('Found item reported! Thank you for helping.')
      navigate('/dashboard')
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Failed to submit report. Please try again.'
      toast.error(msg)
    },
    onSettled: () => {
      release()
    },
  })

  // ── Image upload ────────────────────────────────────────────────────────────
  async function handleImageSelect(file, idx) {
    const ALLOWED = ['image/jpeg', 'image/png', 'image/webp']
    if (!ALLOWED.includes(file.type)) { toast.error('Only JPEG, PNG, and WEBP images are accepted'); return }
    if (file.size > 5 * 1024 * 1024)  { toast.error('Image must be 5 MB or smaller'); return }

    const preview = URL.createObjectURL(file)
    setImages((prev) => { const next = [...prev]; next[idx] = { file, preview, url: null }; return next })
    setUploadingIdx(idx)
    try {
      const url = await uploadImageToCloudinary(file)
      setImages((prev) => { const next = [...prev]; next[idx] = { file, preview, url }; return next })
    } catch (err) {
      toast.error(err.message || 'Image upload failed')
      setImages((prev) => { const next = [...prev]; next[idx] = null; return next })
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

  function setQuestion(id, field, value) {
    setQuestions((prev) =>
      prev.map((q) => (q.id === id ? { ...q, [field]: value } : q)),
    )
  }

  function addQuestion() {
    if (questions.length < 3) setQuestions((prev) => [...prev, newQuestion()])
  }

  function removeQuestion(id) {
    if (questions.length > 2) {
      setQuestions((prev) => prev.filter((q) => q.id !== id))
    }
  }

  // ── Submit ──────────────────────────────────────────────────────────────────
  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return

    if (!category) { release(); return toast.error('Please select a category') }
    if (!description.trim()) { release(); return toast.error('Description is required') }
    if (!dateFound) { release(); return toast.error('Date found is required') }
    if (questions.some((q) => !q.question.trim() || !q.answer.trim())) {
      release()
      return toast.error('All verification questions and answers must be filled in')
    }
    if (uploadingIdx !== null) { release(); return toast.error('Please wait for the image to finish uploading') }

    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)

    // Section 7: submission blocked without at least one photo
    if (imageUrls.length === 0) {
      release()
      return toast.error('At least one photo is required for found items')
    }

    const dateOccurred = timeFound ? `${dateFound}T${timeFound}:00` : `${dateFound}T00:00:00`

    submit({
      category,
      public_description: description.trim(),
      location_id: locationId || null,
      date_occurred: dateOccurred,
      image_urls: imageUrls,
      hidden_questions: questions.map((q) => ({
        question: q.question.trim(),
        answer: q.answer.trim(),
      })),
    })
  }

  const hasRequiredImage = images.some((img) => img?.url)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />

      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Report a Found Item
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Found something on campus? Post it here so the owner can find it.
            A photo is <strong>required</strong> — it helps the owner identify their item.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-7">

          {/* ── Photos (first — most important for found items) ── */}
          <div className="glass p-6">
            <h2 className="section-heading mb-1">Photos <span className="text-red-500">*</span></h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
              At least 1 photo required. Max 2. JPEG, PNG, or WEBP, up to 5 MB each.
            </p>
            <div className="flex gap-4">
              {images.map((img, idx) => (
                <ImageUploadSlot
                  key={idx}
                  index={idx}
                  preview={img?.preview || null}
                  uploading={uploadingIdx === idx}
                  required={idx === 0 && !hasRequiredImage}
                  onSelect={(file) => handleImageSelect(file, idx)}
                  onRemove={() => handleImageRemove(idx)}
                />
              ))}
            </div>
            {!hasRequiredImage && (
              <p className="mt-3 text-xs text-red-500 dark:text-red-400">
                Upload at least one photo before submitting.
              </p>
            )}
          </div>

          {/* ── Item details ── */}
          <div className="glass p-6 relative z-[1] overflow-visible">
            <h2 className="section-heading mb-5">Item Details</h2>
            <div className="flex flex-col gap-5">

              <Field label="Category" required hint="Choose the category that best matches your item.">
                <CategoryPicker value={category} onChange={setCategory} />
              </Field>

              <Field
                label="Description"
                hint="Describe the item as you found it. Be specific but don't reveal details that only the owner would know — that's how verification works."
                required
              >
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  maxLength={1000}
                  placeholder="e.g. Black Samsung phone with cracked screen protector, found near the ICT lab entrance"
                  className="input-field resize-none"
                  required
                />
                <span className="text-xs text-slate-400 text-right">{description.length}/1000</span>
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
                <Field label="Date Found" required>
                  <input
                    type="date"
                    value={dateFound}
                    max={todayMax}
                    onChange={(e) => setDateFound(e.target.value)}
                    className="input-field"
                    required
                  />
                </Field>
                <Field label="Approximate Time">
                  <input
                    type="time"
                    value={timeFound}
                    onChange={(e) => setTimeFound(e.target.value)}
                    className="input-field"
                  />
                </Field>
              </div>
            </div>
          </div>

          <FinderVerificationQuestions
            questions={questions}
            onChange={setQuestion}
            onAdd={addQuestion}
            onRemove={removeQuestion}
          />

          {/* ── Safety note ── */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800
                          rounded-xl p-4 text-xs text-blue-800 dark:text-blue-300">
            <strong>Keep the item safe.</strong> Do not hand it over until ownership is verified through FAiND.
            Once a match is confirmed and both parties agree, the platform will guide the handover process.
          </div>

          {/* ── Actions ── */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="btn-secondary"
              disabled={isSubmitting || isPending}
            >
              Cancel
            </button>
            <SubmitButton
              loading={isSubmitting || isPending}
              disabled={uploadingIdx !== null || !hasRequiredImage}
              className="btn-primary min-w-[140px]"
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
