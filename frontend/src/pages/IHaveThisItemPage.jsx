/**
 * IHaveThisItemPage — Path B (Section 27.9, Feature J).
 *
 * Finder answers owner's hidden questions, location, optional photo (V4.3).
 * Verification runs automatically on submit.
 */
import { useState, useRef, useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import { getPathBForm, submitPathB } from '../services/pathBService'
import { uploadImageToCloudinary } from '../services/itemService'
import { invalidateAfterPathB } from '../utils/queryCache'
import { useCampusZones } from '../hooks/useCampusZones'
import { Check, XCircle, Clock, MapPin, Camera, X } from '../components/icons'

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

function ResultPanel({ result, message, conversationId, attemptsRemaining, onRetry, lostItemId, showPostFoundPrompt }) {
  if (result === 'approved') {
    return (
      <div className="glass p-6 rounded-2xl border border-green-200 dark:border-green-800 text-center">
        <Check className="w-12 h-12 mx-auto mb-3 text-green-600 dark:text-green-400" aria-hidden />
        <h2 className="text-lg font-bold text-green-700 dark:text-green-400 mb-2">
          Claim Approved
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">{message}</p>
        {showPostFoundPrompt && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            You can optionally post this as a found item later for trust recognition.
          </p>
        )}
        <div className="flex flex-col gap-2">
          {conversationId && (
            <Link to={`/messages/${conversationId}`} className="btn-primary text-sm inline-flex justify-center">
              Open Chat
            </Link>
          )}
          <Link to={`/items/${lostItemId}`} className="btn-secondary text-sm inline-flex justify-center">
            Back to Lost Item
          </Link>
        </div>
      </div>
    )
  }

  if (result === 'review') {
    return (
      <div className="glass p-6 rounded-2xl border border-amber-200 dark:border-amber-800 text-center">
        <Clock className="w-12 h-12 mx-auto mb-3 text-amber-600 dark:text-amber-400" aria-hidden />
        <h2 className="text-lg font-bold text-amber-700 dark:text-amber-400 mb-2">
          Under Admin Review
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">{message}</p>
        <Link to={`/items/${lostItemId}`} className="btn-secondary text-sm inline-flex">
          Back to Lost Item
        </Link>
      </div>
    )
  }

  return (
    <div className="glass p-6 rounded-2xl border border-red-200 dark:border-red-800 text-center">
      <XCircle className="w-12 h-12 mx-auto mb-3 text-red-600 dark:text-red-400" aria-hidden />
      <h2 className="text-lg font-bold text-red-700 dark:text-red-400 mb-2">
        Claim Not Approved
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">{message}</p>
      <p className="text-xs text-slate-400 mb-6">
        {attemptsRemaining > 0
          ? `${attemptsRemaining} attempt(s) remaining for this item.`
          : 'No attempts remaining for this item.'}
      </p>
      {attemptsRemaining > 0 ? (
        <button onClick={onRetry} className="btn-secondary text-sm">
          Try Again
        </button>
      ) : (
        <Link to={`/items/${lostItemId}`} className="btn-secondary text-sm inline-flex">
          Back to Lost Item
        </Link>
      )}
    </div>
  )
}

function OptionalPhotoSlot({ preview, uploading, onSelect, onRemove }) {
  const inputRef = useRef(null)
  return (
    <div
      className="relative w-28 h-28 rounded-xl border-2 border-dashed border-slate-300
                 dark:border-slate-600 overflow-hidden flex items-center justify-center
                 cursor-pointer hover:border-brand-400 transition-colors"
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
          <img src={preview} alt="Claim photo" className="w-full h-full object-cover" />
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRemove() }}
            className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5
                       flex items-center justify-center hover:bg-red-700"
          >
            <X className="w-3 h-3" aria-hidden />
          </button>
        </>
      ) : uploading ? (
        <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      ) : (
        <div className="flex flex-col items-center gap-1 text-slate-400">
          <Camera className="w-7 h-7" aria-hidden />
          <span className="text-xs">Optional</span>
        </div>
      )}
    </div>
  )
}

export default function IHaveThisItemPage() {
  const { lostItemId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [answers, setAnswers] = useState({})
  const [locationId, setLocationId] = useState('')
  const [image, setImage] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [resultState, setResultState] = useState(null)

  const { zones, zonesLoading } = useCampusZones()

  const { data: form, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['path-b-form', lostItemId],
    queryFn: () => getPathBForm(lostItemId),
    retry: false,
  })

  const submitMutation = useMutation({
    mutationFn: () =>
      submitPathB(lostItemId, {
        answers: form.questions.map((q) => ({
          question_id: q.id,
          answer: (answers[q.id] || '').trim(),
        })),
        location_id: locationId || null,
        image_url: image?.url || null,
      }),
    onSuccess: (data) => {
      invalidateAfterPathB(queryClient, {
        lostItemId,
        matchId: data.match_id,
      })
      setResultState(data)
      if (data.result === 'approved') {
        toast.success('Claim approved — chat unlocked!')
      } else if (data.result === 'review') {
        toast('Sent for admin review', { icon: <Clock className="w-5 h-5" /> })
      } else {
        toast.error('Claim not approved')
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Claim submission failed')
    },
  })

  async function handleImageSelect(file) {
    setUploading(true)
    try {
      const url = await uploadImageToCloudinary(file)
      setImage({ url, preview: URL.createObjectURL(file) })
    } catch {
      toast.error('Image upload failed')
    } finally {
      setUploading(false)
    }
  }

  function handleAnswerChange(questionId, value) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form?.questions?.every((q) => (answers[q.id] || '').trim())) {
      toast.error('Please answer every verification question')
      return
    }
    submitMutation.mutate()
  }

  const backLink = useMemo(() => `/items/${lostItemId}`, [lostItemId])

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-20 flex justify-center">
          <div className="w-9 h-9 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError) {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 max-w-lg mx-auto text-center">
          <p className="text-sm text-slate-500 mb-6">
            {error.response?.data?.detail || 'This item is not available for claims.'}
          </p>
          <Link to={backLink} className="btn-primary text-sm">Back to Item</Link>
        </div>
      </>
    )
  }

  if (resultState) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 max-w-lg mx-auto">
          <ResultPanel
            result={resultState.result}
            message={resultState.message}
            conversationId={resultState.conversation_id}
            attemptsRemaining={resultState.attempts_remaining}
            lostItemId={lostItemId}
            showPostFoundPrompt={resultState.prompt_post_found_item}
            onRetry={() => {
              setResultState(null)
              setAnswers({})
              refetch()
            }}
          />
        </div>
      </>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-2xl">
        <Link
          to={backLink}
          className="text-sm text-slate-500 hover:text-brand-600 dark:hover:text-brand-400 mb-4 inline-block"
        >
          ← Back to lost item
        </Link>

        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
          I Have This Item
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Answer the owner&apos;s questions by looking at the item you have. Only someone with
          the physical item should know these details.
        </p>

        <div className="glass p-4 rounded-2xl mb-6 border border-slate-200/70 dark:border-slate-700/50">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            Lost item (public view)
          </p>
          <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-4">
            {form.lost_item_public_description}
          </p>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 shrink-0" aria-hidden />
            {form.lost_item_location}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="glass p-6 rounded-2xl flex flex-col gap-5">
          <div className="space-y-5">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Owner&apos;s verification questions
            </p>
            {form.questions.map((q) => (
              <div key={q.id}>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Question {q.position}
                </label>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 p-3
                              rounded-xl bg-slate-100 dark:bg-slate-800/60 mt-1">
                  {q.question}
                </p>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Your answer (inspect the item)"
                  value={answers[q.id] || ''}
                  onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                  maxLength={500}
                  required
                />
              </div>
            ))}
          </div>

          <Field label="Where you found it">
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

          <Field label="Photo" hint="Optional but recommended — compared to the owner's photos if they posted any.">
            <OptionalPhotoSlot
              preview={image?.preview}
              uploading={uploading}
              onSelect={handleImageSelect}
              onRemove={() => setImage(null)}
            />
          </Field>

          <p className="text-xs text-slate-400">
            {form.attempt_counter_paused
              ? 'Your last attempt is under admin review — the attempt counter is paused until a decision is made.'
              : `${form.attempts_remaining} of ${form.max_attempts} attempts remaining for this item.`}
          </p>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={
                submitMutation.isPending
                || form.attempts_remaining === 0
                || form.attempt_counter_paused
              }
              className="btn-primary flex-1 py-3 text-sm font-semibold disabled:opacity-50"
            >
              {submitMutation.isPending ? 'Submitting…' : 'Submit Claim'}
            </button>
            <button
              type="button"
              onClick={() => navigate(backLink)}
              className="btn-secondary px-6 py-3 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
