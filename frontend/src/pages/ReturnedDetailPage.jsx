/**
 * ReturnedDetailPage — Section 16.2 / 27.13 (Feature N).
 */
import { useState, useEffect, useRef } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import TipAppreciationModal from '../components/TipAppreciationModal'
import {
  getReturnDetail,
  skipAppreciation,
  disputeReturn,
} from '../services/returnService'
import { verifyTip } from '../services/tippingService'
import { invalidateAfterReturn } from '../utils/queryCache'
import { getCategoryLabel, Check, MapPin, ChevronLeft, AlertTriangle } from '../components/icons'
import LoadingButton from '../components/LoadingButton'
import { useSubmitLock } from '../hooks/useSubmitLock'

const METHOD_LABEL = {
  dual_confirm: 'Dual confirmation',
  qr_scan: 'QR scan',
}

export default function ReturnedDetailPage() {
  const { returnId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [disputeReason, setDisputeReason] = useState('')
  const [tipModalOpen, setTipModalOpen] = useState(false)
  const verifyStarted = useRef(false)
  const skipLock = useSubmitLock()
  const disputeLock = useSubmitLock()

  const tipVerify = searchParams.get('tip_verify') === '1'
  const tipReference = searchParams.get('reference')

  const { data: detail, isLoading, isError, refetch } = useQuery({
    queryKey: ['return-detail', returnId],
    queryFn: () => getReturnDetail(returnId),
    retry: false,
  })

  const invalidate = () => {
    invalidateAfterReturn(queryClient, {
      returnId,
      matchId: detail?.match_id,
      lostItemId: detail?.lost_item?.id,
      foundItemId: detail?.found_item?.id,
    })
  }

  const skipMutation = useMutation({
    mutationFn: () => skipAppreciation(returnId),
    onSuccess: () => {
      invalidate()
      toast.success('You can send appreciation again in 24 hours.')
      refetch()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not skip'),
    onSettled: () => skipLock.release(),
  })

  const disputeMutation = useMutation({
    mutationFn: () => disputeReturn(returnId, disputeReason.trim()),
    onSuccess: () => {
      invalidate()
      toast.success('Dispute submitted. An admin will review this return.')
      setDisputeOpen(false)
      setDisputeReason('')
      refetch()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not file dispute'),
    onSettled: () => disputeLock.release(),
  })

  useEffect(() => {
    if (!tipVerify || !tipReference || verifyStarted.current) return
    verifyStarted.current = true

    verifyTip(tipReference)
      .then((result) => {
        if (result.status === 'success') {
          toast.success(result.message || 'Appreciation sent successfully.')
          invalidateAfterReturn(queryClient, { returnId })
          refetch()
        } else if (result.status === 'pending') {
          toast('Payment is still processing. Refresh in a moment if needed.', { icon: '⏳' })
        } else {
          toast.error(result.message || 'Could not verify payment.')
        }
      })
      .catch((err) => {
        toast.error(err.response?.data?.detail || 'Could not verify payment.')
      })
      .finally(() => {
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev)
          next.delete('tip_verify')
          next.delete('reference')
          return next
        }, { replace: true })
      })
  }, [tipVerify, tipReference, returnId, queryClient, refetch, setSearchParams])

  if (isLoading) {
    return (
      <>
        <NavBar />
        <div className="page-container py-16 flex justify-center">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    )
  }

  if (isError || !detail) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 text-center text-slate-500">
          Return not found or you do not have access.
          <div className="mt-4">
            <Link to="/dashboard?tab=returned" className="btn-secondary text-sm">Dashboard</Link>
          </div>
        </div>
      </>
    )
  }

  const images = detail.lost_item?.image_urls?.length
    ? detail.lost_item.image_urls
    : detail.found_item?.image_urls || []

  const chatHref = detail.conversation_id
    ? `/messages/${detail.conversation_id}`
    : null

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-2xl">
        <Link
          to="/dashboard?tab=returned"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 mb-6"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden />
          Returned items
        </Link>

        <div className="flex items-start gap-3 mb-6 flex-wrap">
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold
                           bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400">
            <Check className="w-3.5 h-3.5" aria-hidden />
            Resolved
          </span>
          {detail.dispute_active && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold
                             bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden />
              Under dispute
            </span>
          )}
          <span className="text-xs text-slate-400 self-center">
            {METHOD_LABEL[detail.method] || detail.method}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-1">
          {detail.item_label || getCategoryLabel(detail.category)}
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Returned {new Date(detail.returned_at).toLocaleString()}
        </p>

        {detail.summary_note && !detail.appreciation_message && (
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-4 glass p-4 rounded-xl">
            {detail.summary_note}
          </p>
        )}

        <div className="glass p-5 mb-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">With</h2>
          <p className="font-medium text-slate-800 dark:text-slate-100">
            {detail.other_user?.display_name}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {detail.other_user?.trust_tier}
            {detail.viewer_role === 'lost_owner' ? ' · Finder' : ' · Owner'}
          </p>
        </div>

        <div className="glass p-5 mb-6 space-y-2 text-sm">
          <h2 className="font-semibold text-slate-700 dark:text-slate-300 mb-2">Timeline</h2>
          {detail.dates_summary?.lost && (
            <p><span className="text-slate-400">Lost:</span> {new Date(detail.dates_summary.lost).toLocaleDateString()}</p>
          )}
          {detail.dates_summary?.found && (
            <p><span className="text-slate-400">Found:</span> {new Date(detail.dates_summary.found).toLocaleDateString()}</p>
          )}
          {detail.dates_summary?.returned && (
            <p><span className="text-slate-400">Returned:</span> {new Date(detail.dates_summary.returned).toLocaleString()}</p>
          )}
        </div>

        <div className="glass p-5 mb-6">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
            {detail.lost_item?.public_description}
          </p>
          <p className="text-xs text-slate-400 flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" aria-hidden />
            {detail.found_item?.location_label}
          </p>
        </div>

        {images.length > 0 && (
          <div className="flex gap-2 overflow-x-auto mb-6">
            {images.map((url) => (
              <img
                key={url}
                src={url}
                alt=""
                className="w-24 h-24 rounded-xl object-cover flex-shrink-0"
              />
            ))}
          </div>
        )}

        {detail.dispute_active && detail.dispute_reason && (
          <div className="glass p-5 mb-4 border border-red-200/60 dark:border-red-800/40">
            <h2 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">Dispute details</h2>
            <p className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
              {detail.dispute_reason}
            </p>
            {detail.tip_frozen && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
                Any appreciation payment is frozen pending admin review.
              </p>
            )}
          </div>
        )}

        {detail.appreciation_message && (
          <div className="glass p-4 mb-4 text-sm text-teal-700 dark:text-teal-300">
            {detail.appreciation_message}
          </div>
        )}

        {detail.appreciation_sent && detail.viewer_role === 'lost_owner' && (
          <div className="glass p-4 mb-4 text-sm text-teal-700 dark:text-teal-300">
            You sent appreciation to the finder.
            {detail.tip_frozen && ' (Frozen while dispute is open.)'}
          </div>
        )}

        {detail.can_send_appreciation && (
          <div className="glass p-5 mb-4 border border-brand-200/50 dark:border-brand-800/30">
            <h2 className="text-sm font-semibold mb-1">Send appreciation</h2>
            <p className="text-xs text-slate-500 mb-3">
              {detail.tipping_days_left > 0
                ? `${detail.tipping_days_left} day${detail.tipping_days_left !== 1 ? 's' : ''} left to send appreciation`
                : 'Tipping window closing soon'}
            </p>
            {!detail.paystack_ready && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mb-3">
                Payments are not configured on this server yet. Contact your administrator.
              </p>
            )}
            <button
              type="button"
              className="btn-primary w-full py-2.5 text-sm mb-2"
              disabled={!detail.paystack_ready}
              onClick={() => setTipModalOpen(true)}
            >
              Send Appreciation
            </button>
            {detail.can_skip_appreciation && (
              <LoadingButton
                className="btn-secondary w-full py-2.5 text-sm"
                loading={skipLock.isSubmitting || skipMutation.isPending}
                disabled={skipLock.isSubmitting || skipMutation.isPending}
                loadingLabel="Saving…"
                onClick={() => {
                  if (!skipLock.tryAcquire()) return
                  skipMutation.mutate()
                }}
              >
                Skip for Now
              </LoadingButton>
            )}
          </div>
        )}

        {detail.can_dispute && !disputeOpen && (
          <button
            type="button"
            onClick={() => setDisputeOpen(true)}
            className="w-full py-2.5 text-sm rounded-xl border border-red-200 text-red-600
                       hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20 mb-4"
          >
            Dispute This Return
            {detail.dispute_days_left > 0 && (
              <span className="block text-xs font-normal mt-0.5 opacity-80">
                {detail.dispute_days_left} day{detail.dispute_days_left !== 1 ? 's' : ''} left
              </span>
            )}
          </button>
        )}

        {disputeOpen && (
          <div className="glass p-5 mb-4 border border-red-200/60 dark:border-red-800/40">
            <h2 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-2">
              Dispute this return
            </h2>
            <textarea
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
              rows={4}
              placeholder="Explain why you are disputing this return (min. 10 characters)…"
              className="input-field w-full text-sm mb-3"
            />
            <div className="flex gap-2">
              <button
                type="button"
                className="btn-secondary flex-1 py-2 text-sm"
                onClick={() => {
                  setDisputeOpen(false)
                  setDisputeReason('')
                }}
              >
                Cancel
              </button>
              <LoadingButton
                className="flex-1 py-2 text-sm rounded-xl bg-red-600 text-white hover:bg-red-700
                           disabled:opacity-50"
                loading={disputeLock.isSubmitting || disputeMutation.isPending}
                disabled={
                  disputeReason.trim().length < 10
                  || disputeLock.isSubmitting
                  || disputeMutation.isPending
                }
                loadingLabel="Submitting…"
                onClick={() => {
                  if (!disputeLock.tryAcquire()) return
                  disputeMutation.mutate()
                }}
              >
                Submit Dispute
              </LoadingButton>
            </div>
          </div>
        )}

        {chatHref && (
          <Link
            to={chatHref}
            className="btn-secondary w-full text-center text-sm py-3 block"
          >
            {detail.chat_read_only ? 'View chat history (read-only)' : 'Open chat'}
          </Link>
        )}
      </div>

      <TipAppreciationModal
        open={tipModalOpen}
        onClose={() => setTipModalOpen(false)}
        returnId={returnId}
        daysLeft={detail?.tipping_days_left ?? 0}
      />
    </div>
  )
}
