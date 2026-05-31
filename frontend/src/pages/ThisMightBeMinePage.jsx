/**
 * ThisMightBeMinePage — Path C (V4.4).
 *
 * Owner answers finder's hidden questions only.
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import { getPathCForm, submitPathC } from '../services/pathCService'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { invalidateAfterPathC } from '../utils/queryCache'
import { Check, XCircle, Clock, MapPin } from '../components/icons'

function ResultPanel({
  result,
  message,
  conversationId,
  attemptsRemaining,
  onRetry,
  foundItemId,
  showPostLostPrompt,
}) {
  if (result === 'approved') {
    return (
      <div className="glass p-6 rounded-2xl border border-green-200 dark:border-green-800 text-center">
        <Check className="w-12 h-12 mx-auto mb-3 text-green-600 dark:text-green-400" aria-hidden />
        <h2 className="text-lg font-bold text-green-700 dark:text-green-400 mb-2">
          Ownership Verified
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">{message}</p>
        {showPostLostPrompt && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            You can optionally post a full lost item report later for your records.
          </p>
        )}
        <div className="flex flex-col gap-2">
          {conversationId && (
            <Link
              to={`/messages/${conversationId}`}
              className="btn-primary text-sm inline-flex justify-center"
            >
              Open Chat
            </Link>
          )}
          <Link
            to={`/items/${foundItemId}`}
            className="btn-secondary text-sm inline-flex justify-center"
          >
            Back to Found Item
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
        <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-4">
          Your claim is under review
        </p>
        <Link to={`/items/${foundItemId}`} className="btn-secondary text-sm inline-flex">
          Back to Found Item
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
        <Link to={`/items/${foundItemId}`} className="btn-secondary text-sm inline-flex">
          Back to Found Item
        </Link>
      )}
    </div>
  )
}

export default function ThisMightBeMinePage() {
  const { foundItemId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [answers, setAnswers] = useState({})
  const [resultState, setResultState] = useState(null)
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const { data: form, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['path-c-form', foundItemId],
    queryFn: () => getPathCForm(foundItemId),
    retry: false,
  })

  const submitMutation = useMutation({
    mutationFn: () =>
      submitPathC(foundItemId, {
        answers: form.questions.map((q) => ({
          question_id: q.id,
          answer: (answers[q.id] || '').trim(),
        })),
      }),
    onSuccess: (data) => {
      invalidateAfterPathC(queryClient, { foundItemId, matchId: data.match_id })
      setResultState(data)
      if (data.result === 'approved') {
        toast.success('Ownership verified — chat unlocked!')
      } else if (data.result === 'review') {
        toast('Sent for admin review', { icon: <Clock className="w-5 h-5" /> })
      } else {
        toast.error('Claim not approved')
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Claim submission failed')
    },
    onSettled: () => {
      release()
    },
  })

  function handleAnswerChange(questionId, value) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    if (!form?.questions?.every((q) => (answers[q.id] || '').trim())) {
      release()
      toast.error('Please answer every verification question')
      return
    }
    submitMutation.mutate()
  }

  const backLink = `/items/${foundItemId}`

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
            foundItemId={foundItemId}
            showPostLostPrompt={resultState.prompt_post_lost_item}
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
          ← Back to found item
        </Link>

        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
          This Might Be Mine
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Answer the finder&apos;s verification questions from memory to prove this item is yours.
        </p>

        <div className="glass p-4 rounded-2xl mb-6 border border-slate-200/70 dark:border-slate-700/50">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            Found item (public view)
          </p>
          <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-4">
            {form.found_item_public_description}
          </p>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 shrink-0" aria-hidden />
            {form.found_item_location}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="glass p-6 rounded-2xl flex flex-col gap-5">
          <div className="space-y-5">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              Finder&apos;s verification questions
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
                  placeholder="Your answer from memory"
                  value={answers[q.id] || ''}
                  onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                  maxLength={500}
                  required
                />
              </div>
            ))}
          </div>

          <p className="text-xs text-slate-400">
            {form.attempt_counter_paused
              ? 'Your last attempt is under admin review — the attempt counter is paused until a decision is made.'
              : `${form.attempts_remaining} of ${form.max_attempts} attempts remaining for this item.`}
          </p>

          <div className="flex gap-3 pt-2">
            <SubmitButton
              loading={isSubmitting || submitMutation.isPending}
              disabled={form.attempts_remaining === 0 || form.attempt_counter_paused}
              className="btn-primary flex-1 py-3 text-sm font-semibold disabled:opacity-50"
              loadingLabel="Submitting…"
            >
              Submit Claim
            </SubmitButton>
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
