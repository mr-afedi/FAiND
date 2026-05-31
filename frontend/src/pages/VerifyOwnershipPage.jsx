/**
 * VerifyOwnershipPage — Path A verification form (Section 27.8).
 *
 * Lost item owner answers the finder's hidden verification questions (V4.2).
 * Results: Passed → Open Chat | Admin Review → info | Rejected → retry info.
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import { getPathAForm, submitPathA } from '../services/verificationService'
import SubmitButton from '../components/SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { invalidateAfterVerification } from '../utils/queryCache'
import { Check, XCircle, Lock, MapPin, Clock } from '../components/icons'

function ResultPanel({ result, message, conversationId, attemptsRemaining, onRetry }) {
  if (result === 'approved') {
    return (
      <div className="glass p-6 rounded-2xl border border-green-200 dark:border-green-800 text-center">
        <Check className="w-12 h-12 mx-auto mb-3 text-green-600 dark:text-green-400" aria-hidden />
        <h2 className="text-lg font-bold text-green-700 dark:text-green-400 mb-2">
          Verification Passed
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">{message}</p>
        {conversationId && (
          <Link to={`/messages/${conversationId}`} className="btn-primary text-sm inline-flex">
            Open Chat
          </Link>
        )}
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
        <Link to="/dashboard?tab=pending" className="btn-secondary text-sm inline-flex">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="glass p-6 rounded-2xl border border-red-200 dark:border-red-800 text-center">
      <XCircle className="w-12 h-12 mx-auto mb-3 text-red-600 dark:text-red-400" aria-hidden />
      <h2 className="text-lg font-bold text-red-700 dark:text-red-400 mb-2">
        Verification Failed
      </h2>
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">{message}</p>
      <p className="text-xs text-slate-400 mb-6">
        {attemptsRemaining > 0
          ? `${attemptsRemaining} attempt(s) remaining in the next 24 hours.`
          : 'No attempts remaining in the next 24 hours.'}
      </p>
      {attemptsRemaining > 0 ? (
        <button onClick={onRetry} className="btn-secondary text-sm">
          Try Again
        </button>
      ) : (
        <Link to="/dashboard?tab=pending" className="btn-secondary text-sm inline-flex">
          Back to Dashboard
        </Link>
      )}
    </div>
  )
}

export default function VerifyOwnershipPage() {
  const { matchId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [answers, setAnswers] = useState({})
  const [resultState, setResultState] = useState(null)
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const { data: form, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['path-a-form', matchId],
    queryFn: () => getPathAForm(matchId),
    retry: false,
  })

  const submitMutation = useMutation({
    mutationFn: () =>
      submitPathA(
        matchId,
        form.questions.map((q) => ({
          question_id: q.id,
          answer: answers[q.id]?.trim() || '',
        })),
      ),
    onSuccess: (data) => {
      invalidateAfterVerification(queryClient, {
        matchId,
        lostItemId: form?.lost_item_id,
        foundItemId: form?.found_item_id,
      })
      setResultState(data)
      if (data.result === 'approved') {
        toast.success('Verification passed!')
      } else if (data.result === 'review') {
        toast('Sent for admin review', { icon: <Clock className="w-5 h-5" /> })
      } else {
        toast.error('Verification failed')
      }
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Verification submission failed')
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
    if (!form?.questions.every((q) => answers[q.id]?.trim())) {
      release()
      toast.error('Please answer all verification questions')
      return
    }
    submitMutation.mutate()
  }

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
          <Lock className="w-14 h-14 mx-auto mb-4 text-slate-400" aria-hidden />
          <h1 className="text-xl font-semibold mb-2">Cannot open verification</h1>
          <p className="text-sm text-slate-500 mb-6">
            {error.response?.data?.detail || 'This match is not available for verification.'}
          </p>
          <Link to="/dashboard?tab=pending" className="btn-primary text-sm">
            Back to Dashboard
          </Link>
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
            attemptsRemaining={resultState.attempts_remaining_24h}
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
          to="/dashboard?tab=pending"
          className="text-sm text-slate-500 hover:text-brand-600 dark:hover:text-brand-400 mb-4 inline-block"
        >
          ← Back to Pending Matches
        </Link>

        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
          Verify Ownership
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Answer the finder&apos;s verification questions about this item to prove it is yours.
          Answers are compared using AI semantic matching — exact wording is not required.
        </p>

        {/* Matched found item preview */}
        <div className="glass p-4 rounded-2xl mb-6 border border-violet-200/60 dark:border-violet-800/40">
          <p className="text-xs font-semibold text-violet-600 dark:text-violet-400 mb-1">
            Matched found item
          </p>
          <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-3">
            {form.found_item_description}
          </p>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5 shrink-0" aria-hidden />
            {form.found_item_location}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="glass p-6 rounded-2xl space-y-5">
          {form.questions.map((q) => (
            <div key={q.id}>
              <label className="label">
                Question {q.position}
              </label>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2 p-3
                            rounded-xl bg-slate-100 dark:bg-slate-800/60">
                {q.question}
              </p>
              <input
                type="text"
                className="input w-full"
                placeholder="Your answer"
                value={answers[q.id] || ''}
                onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                maxLength={500}
                required
              />
            </div>
          ))}

          <p className="text-xs text-slate-400">
            {form.attempts_remaining_24h} of {form.max_attempts_24h} attempts remaining in the
            next 24 hours.
          </p>

          <div className="flex gap-3 pt-2">
            <SubmitButton
              loading={isSubmitting || submitMutation.isPending}
              disabled={form.attempts_remaining_24h === 0}
              className="btn-primary flex-1 py-3 text-sm font-semibold disabled:opacity-50"
              loadingLabel="Verifying…"
            >
              Submit Verification
            </SubmitButton>
            <button
              type="button"
              onClick={() => navigate('/dashboard?tab=pending')}
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
