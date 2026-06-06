/**
 * Feature C — Report Lost Item (Section 6, V4.3)
 *
 * Public description, 2–3 hidden verification Q&A, location, date, optional images.
 */
import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import OwnerVerificationQuestions from '../components/OwnerVerificationQuestions'
import {
  createLostItem,
  checkLostHiddenAnswers,
  uploadImageToCloudinary,
} from '../services/itemService'
import { invalidateAfterItemCreate } from '../utils/queryCache'
import { useCampusZones, createInitialQuestions, newQuestion } from '../hooks/useCampusZones'
import { X } from '../components/icons'
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

function ImageUploadSlot({ index, preview, uploading, onSelect, onRemove }) {
  const inputRef = useRef(null)
  return (
    <div
      className="relative w-28 h-28 rounded-xl border-2 border-dashed
                    border-slate-300 dark:border-slate-600 overflow-hidden
                    flex items-center justify-center cursor-pointer
                    hover:border-brand-400 transition-colors"
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

function mapWarningsToQuestions(questions, warnings) {
  const map = {}
  questions.forEach((q, idx) => {
    const prefix = `Question ${idx + 1}:`
    const match = warnings.find((w) => w.startsWith(prefix))
    if (match) map[q.id] = match
  })
  return map
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
  const [questions, setQuestions] = useState(() => createInitialQuestions(2))
  const [answerWarnings, setAnswerWarnings] = useState({})

  const todayMax = useMemo(() => new Date().toISOString().split('T')[0], [])
  const { zones, zonesLoading } = useCampusZones()
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const refreshWarnings = useCallback(async () => {
    const filled = questions.filter((q) => q.question.trim() && q.answer.trim())
    if (!publicDesc.trim() || filled.length < 2) {
      setAnswerWarnings({})
      return
    }
    try {
      const { warnings } = await checkLostHiddenAnswers({
        public_description: publicDesc.trim(),
        hidden_questions: filled.map((q) => ({
          question: q.question.trim(),
          answer: q.answer.trim(),
        })),
      })
      setAnswerWarnings(mapWarningsToQuestions(questions, warnings || []))
    } catch {
      /* non-blocking */
    }
  }, [publicDesc, questions])

  useEffect(() => {
    const t = setTimeout(refreshWarnings, 400)
    return () => clearTimeout(t)
  }, [refreshWarnings])

  function handleQuestionChange(id, field, value) {
    setQuestions((prev) =>
      prev.map((q) => (q.id === id ? { ...q, [field]: value } : q)),
    )
  }

  function handleAddQuestion() {
    if (questions.length >= 3) return
    setQuestions((prev) => [...prev, newQuestion()])
  }

  function handleRemoveQuestion(id) {
    if (questions.length <= 2) return
    setQuestions((prev) => prev.filter((q) => q.id !== id))
    setAnswerWarnings((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }

  const { mutate: submit, isPending } = useMutation({
    mutationFn: createLostItem,
    onSuccess: (data) => {
      invalidateAfterItemCreate(queryClient, { type: 'lost' })
      if (data.warnings?.length) {
        data.warnings.forEach((w) => toast(w, { icon: '⚠️', duration: 6000 }))
      }
      toast.success('Lost item reported successfully!')
      navigate('/dashboard')
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to submit report. Please try again.')
    },
    onSettled: () => {
      release()
    },
  })

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
    const validQs = questions.filter((q) => q.question.trim() && q.answer.trim())
    if (validQs.length < 2) {
      release()
      return toast.error('Please provide at least 2 verification questions with answers')
    }
    if (uploadingIdx !== null) {
      release()
      return toast.error('Please wait for the image to finish uploading')
    }

    const imageUrls = images.filter((img) => img?.url).map((img) => img.url)
    const dateOccurred = timeLost
      ? `${dateLost}T${timeLost}:00`
      : `${dateLost}T00:00:00`

    submit({
      category,
      public_description: publicDesc.trim(),
      location_id: locationId || null,
      date_occurred: dateOccurred,
      image_urls: imageUrls,
      hidden_questions: validQs.map((q) => ({
        question: q.question.trim(),
        answer: q.answer.trim(),
      })),
    })
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />

      <div className="max-w-2xl mx-auto px-4 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Report a Lost Item
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Your hidden questions help verify someone who finds your item. Answers are encrypted
            and never shown to anyone after you submit.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-7">
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
            </div>
          </div>

          <OwnerVerificationQuestions
            questions={questions}
            onChange={handleQuestionChange}
            onAdd={handleAddQuestion}
            onRemove={handleRemoveQuestion}
            answerWarnings={answerWarnings}
          />

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
              disabled={uploadingIdx !== null}
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
