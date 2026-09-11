/**
 * Report post or user modal (Section 13).
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { X } from './icons'
import SubmitButton from './SubmitButton'
import { useSubmitLock } from '../hooks/useSubmitLock'
import { POST_REPORT_REASONS, USER_REPORT_REASONS } from '../constants/reportReasons'
import { reportPost, reportUser } from '../services/reportService'

export default function ReportModal({
  open,
  onClose,
  type,
  targetId,
  conversationId = null,
  targetLabel = '',
}) {
  const [reason, setReason] = useState('')
  const [detailText, setDetailText] = useState('')
  const { isSubmitting, tryAcquire, release } = useSubmitLock()

  const reasons = type === 'post' ? POST_REPORT_REASONS : USER_REPORT_REASONS
  const needsDetail = reason === 'other'

  const mutation = useMutation({
    mutationFn: () => {
      const payload = { reason, detail_text: needsDetail ? detailText.trim() : null }
      if (type === 'post') {
        return reportPost(targetId, payload)
      }
      return reportUser(targetId, {
        ...payload,
        conversation_id: conversationId,
      })
    },
    onSuccess: (data) => {
      toast.success(data.message || 'Report submitted.')
      if (data.auto_escalated) {
        toast('This report was flagged for priority review.', { icon: '⚠️' })
      }
      setReason('')
      setDetailText('')
      onClose()
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Could not submit report.')
    },
    onSettled: () => release(),
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!tryAcquire()) return
    if (!reason) {
      release()
      toast.error('Please select a reason')
      return
    }
    if (needsDetail && !detailText.trim()) {
      release()
      toast.error('Please describe the issue when selecting Other')
      return
    }
    mutation.mutate()
  }

  if (!open) return null

  const title = type === 'post' ? 'Report this post' : 'Report user'
  const busy = isSubmitting || mutation.isPending

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-modal-title"
    >
      <div className="glass w-full max-w-md rounded-2xl p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <h2 id="report-modal-title" className="text-lg font-bold text-slate-800 dark:text-slate-100">
              {title}
            </h2>
            {targetLabel && (
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{targetLabel}</p>
            )}
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

        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Reports are reviewed by moderators. Misuse of reporting may result in action on your account.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="report-reason">Reason</label>
            <select
              id="report-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="input-field w-full"
              required
              disabled={busy}
            >
              <option value="">Select a reason…</option>
              {reasons.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          {needsDetail && (
            <div>
              <label className="label" htmlFor="report-detail">
                Additional details (required)
              </label>
              <textarea
                id="report-detail"
                value={detailText}
                onChange={(e) => setDetailText(e.target.value)}
                maxLength={200}
                rows={3}
                className="input-field w-full text-sm"
                placeholder="Describe the issue…"
                disabled={busy}
                required
              />
              <p className="text-xs text-slate-400 mt-1">{detailText.length}/200</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              className="btn-secondary flex-1"
              onClick={onClose}
              disabled={busy}
            >
              Cancel
            </button>
            <SubmitButton
              loading={busy}
              className="btn-primary flex-1"
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
