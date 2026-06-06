/**
 * Send appreciation via Paystack (Section 20).
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { X } from './icons'
import SubmitButton from './SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { initializeTip } from '../services/tippingService'

const PRESET_AMOUNTS = [5, 10, 20, 50]

export default function TipAppreciationModal({ open, onClose, returnId, daysLeft }) {
  const [amount, setAmount] = useState('')
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const mutation = useMutation({
    mutationFn: () => initializeTip(returnId, parseFloat(amount)),
    onSuccess: (data) => {
      toast.success('Redirecting to secure checkout…')
      window.location.href = data.authorization_url
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Could not start payment.')
      release()
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    const value = parseFloat(amount)
    if (!value || value < 1) {
      release()
      toast.error('Enter an amount of at least GHS 1.00')
      return
    }
    if (value > 500) {
      release()
      toast.error('Maximum amount is GHS 500.00')
      return
    }
    mutation.mutate()
  }

  if (!open) return null

  const busy = isSubmitting || mutation.isPending

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      role="dialog"
      aria-modal="true"
    >
      <div className="glass w-full max-w-md rounded-2xl p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">
              Send appreciation
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Optional — does not affect trust score.{' '}
              {daysLeft > 0 && `${daysLeft} day${daysLeft !== 1 ? 's' : ''} left in the window.`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="w-5 h-5" aria-hidden />
          </button>
        </div>

        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
          You will be redirected to Paystack (test mode) to complete payment securely.
          The finder will not see the amount — only that you sent appreciation.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {PRESET_AMOUNTS.map((preset) => (
              <button
                key={preset}
                type="button"
                disabled={busy}
                onClick={() => setAmount(String(preset))}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  amount === String(preset)
                    ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                    : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                }`}
              >
                GHS {preset}
              </button>
            ))}
          </div>

          <div>
            <label className="label" htmlFor="tip-amount">Custom amount (GHS)</label>
            <input
              id="tip-amount"
              type="number"
              min="1"
              max="500"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input-field w-full"
              placeholder="e.g. 15.00"
              disabled={busy}
              required
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-secondary flex-1" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <SubmitButton loading={busy} className="btn-primary flex-1" loadingLabel="Starting…">
              Continue to Paystack
            </SubmitButton>
          </div>
        </form>
      </div>
    </div>
  )
}
