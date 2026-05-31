/**
 * ReturnConfirmPage — dual confirm + QR return flow (Section 15, Feature M).
 */
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import NavBar from '../components/NavBar'
import { getCategoryLabel } from '../components/icons'
import {
  getReturnStatus,
  finderConfirmHandover,
  ownerConfirmReceipt,
  generateReturnQr,
  redeemReturnQr,
} from '../services/returnService'
import { invalidateAfterReturn } from '../utils/queryCache'
import { Check, Hand, ScanSearch, ChevronLeft } from '../components/icons'

function ItemPreview({ item, label }) {
  if (!item) return null
  return (
    <div className="rounded-xl border border-slate-200/80 dark:border-slate-700/50 p-4">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="font-semibold text-slate-800 dark:text-slate-100">
        {getCategoryLabel(item.category)}
      </p>
      <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 line-clamp-2">
        {item.public_description}
      </p>
      <p className="text-xs text-slate-400 mt-2">{item.location_label}</p>
    </div>
  )
}

export default function ReturnConfirmPage() {
  const { matchId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [qrPayload, setQrPayload] = useState(null)
  const [qrExpires, setQrExpires] = useState(null)
  const [pasteToken, setPasteToken] = useState('')

  const { data: status, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['return-status', matchId],
    queryFn: () => getReturnStatus(matchId),
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data
      return data && !data.is_complete ? 5000 : false
    },
  })

  const invalidate = () => {
    invalidateAfterReturn(queryClient, {
      matchId,
      returnId: status?.return_id,
      lostItemId: status?.lost_item?.id,
      foundItemId: status?.found_item?.id,
    })
  }

  const finderMutation = useMutation({
    mutationFn: () => finderConfirmHandover(matchId),
    onSuccess: (data) => {
      invalidate()
      toast.success(data.message)
      if (data.completed && data.status?.return_id) {
        navigate(`/returns/${data.status.return_id}`)
      } else {
        refetch()
      }
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not confirm handover'),
  })

  const ownerMutation = useMutation({
    mutationFn: () => ownerConfirmReceipt(matchId),
    onSuccess: (data) => {
      invalidate()
      toast.success(data.message)
      if (data.completed && data.status?.return_id) {
        navigate(`/returns/${data.status.return_id}`)
      } else {
        refetch()
      }
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not confirm receipt'),
  })

  const qrGenerateMutation = useMutation({
    mutationFn: () => generateReturnQr(matchId),
    onSuccess: (data) => {
      invalidate()
      setQrPayload(data.qr_payload)
      setQrExpires(data.expires_at)
      toast.success('QR code generated — valid for 24 hours')
      refetch()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not generate QR code'),
  })

  const qrRedeemMutation = useMutation({
    mutationFn: () => redeemReturnQr(pasteToken.trim()),
    onSuccess: (data) => {
      invalidate()
      toast.success(data.message)
      if (data.status?.return_id) {
        navigate(`/returns/${data.status.return_id}`)
      }
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Invalid or expired QR code'),
  })

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

  if (isError) {
    const detail = error?.response?.data?.detail || 'Unable to load return confirmation.'
    return (
      <>
        <NavBar />
        <div className="page-container py-10 max-w-lg mx-auto text-center">
          <p className="text-slate-600 dark:text-slate-400 mb-6">{detail}</p>
          <Link to="/dashboard" className="btn-secondary text-sm">Back to Dashboard</Link>
        </div>
      </>
    )
  }

  if (status?.is_complete) {
    return (
      <>
        <NavBar />
        <div className="page-container py-10 max-w-lg mx-auto">
          <div className="glass p-6 rounded-2xl border border-teal-200 dark:border-teal-800 text-center">
            <Check className="w-12 h-12 mx-auto mb-3 text-teal-600 dark:text-teal-400" aria-hidden />
            <h1 className="text-lg font-bold text-teal-700 dark:text-teal-400 mb-2">
              Return Complete
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
              This item has already been marked as returned.
            </p>
            <Link to={`/returns/${status.return_id}`} className="btn-primary text-sm inline-flex">
              View Return Details
            </Link>
          </div>
        </div>
      </>
    )
  }

  const isFinder = status.viewer_role === 'found_owner'
  const isOwner = status.viewer_role === 'lost_owner'
  const qrImgUrl = qrPayload
    ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(qrPayload)}`
    : null

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <div className="page-container py-8 max-w-2xl">
        <Link
          to="/dashboard?tab=pending"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-600 mb-6"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden />
          Back
        </Link>

        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Confirm Return
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Complete the handover using dual confirmation or a one-time QR code.
        </p>

        <div className="grid sm:grid-cols-2 gap-4 mb-6">
          <ItemPreview item={status.lost_item} label="Lost item" />
          <ItemPreview item={status.found_item} label="Found item" />
        </div>

        {/* Progress */}
        <div className="glass p-4 mb-6 flex flex-col sm:flex-row gap-4 sm:gap-8">
          <div className="flex items-center gap-2 text-sm">
            <span className={`w-2.5 h-2.5 rounded-full ${status.finder_handed_over ? 'bg-teal-500' : 'bg-slate-300'}`} />
            Finder handed over
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className={`w-2.5 h-2.5 rounded-full ${status.owner_received ? 'bg-teal-500' : 'bg-slate-300'}`} />
            Owner received
          </div>
        </div>

        {/* Dual confirm */}
        <section className="glass p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <Hand className="w-4 h-4" aria-hidden />
            Dual confirmation
          </h2>

          {status.awaiting_owner_receipt && (
            <div className="mb-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200/80
                            dark:border-amber-800/50 text-center">
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
                Action needed
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                The finder confirmed they handed over your item. Confirm receipt below when you have it.
              </p>
            </div>
          )}

          {status.awaiting_finder_handover && (
            <p className="text-sm text-slate-500 text-center mb-4">
              You confirmed receipt. Waiting for the finder to confirm they handed over the item.
            </p>
          )}

          {isFinder && status.can_confirm_finder && (
            <button
              type="button"
              onClick={() => finderMutation.mutate()}
              disabled={finderMutation.isPending}
              className="btn-primary w-full py-3 text-sm"
            >
              {finderMutation.isPending ? 'Confirming…' : 'I handed over the item'}
            </button>
          )}
          {isOwner && status.can_confirm_owner && (
            <button
              type="button"
              onClick={() => ownerMutation.mutate()}
              disabled={ownerMutation.isPending}
              className="btn-primary w-full py-3 text-sm"
            >
              {ownerMutation.isPending ? 'Confirming…' : 'I received my item'}
            </button>
          )}
          {isFinder && !status.can_confirm_finder && status.finder_handed_over && (
            <p className="text-sm text-slate-500 text-center">
              You confirmed handover. Waiting for the owner to confirm receipt.
            </p>
          )}
          {!status.can_confirm_finder && !status.can_confirm_owner
            && !status.finder_handed_over && !status.owner_received
            && !status.awaiting_owner_receipt && !status.awaiting_finder_handover && (
            <p className="text-sm text-slate-500 text-center">
              {isFinder
                ? 'Confirm when you physically hand the item to the owner, or use QR below.'
                : 'Confirm when you receive your item, or scan the finder\'s QR code below.'}
            </p>
          )}
        </section>

        {/* QR */}
        <section className="glass p-6">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
            <ScanSearch className="w-4 h-4" aria-hidden />
            QR code (24h, single use)
          </h2>

          {isFinder && (
            <div className="space-y-4">
              {status.can_generate_qr && (
                <button
                  type="button"
                  onClick={() => qrGenerateMutation.mutate()}
                  disabled={qrGenerateMutation.isPending}
                  className="btn-secondary w-full py-2.5 text-sm"
                >
                  {qrGenerateMutation.isPending ? 'Generating…' : 'Generate QR code'}
                </button>
              )}
              {(status.qr_active || qrPayload) && (
                <div className="text-center">
                  {qrImgUrl && (
                    <img
                      src={qrImgUrl}
                      alt="Return QR code"
                      className="mx-auto rounded-lg border border-slate-200 dark:border-slate-700"
                      width={220}
                      height={220}
                    />
                  )}
                  {qrPayload && (
                    <p className="text-xs text-slate-400 mt-3 break-all font-mono px-2">
                      {qrPayload}
                    </p>
                  )}
                  {(qrExpires || status.qr_expires_at) && (
                    <p className="text-xs text-slate-500 mt-2">
                      Expires {new Date(qrExpires || status.qr_expires_at).toLocaleString()}
                    </p>
                  )}
                  <p className="text-xs text-slate-400 mt-2">
                    Show this to the owner to scan, or they can paste the code below.
                  </p>
                </div>
              )}
            </div>
          )}

          {isOwner && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500">
                Paste the QR payload from the finder&apos;s screen, or scan with your camera app
                and paste the result here.
              </p>
              <input
                type="text"
                value={pasteToken}
                onChange={(e) => setPasteToken(e.target.value)}
                placeholder="faind-return:…"
                className="input-field w-full text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => qrRedeemMutation.mutate()}
                disabled={!pasteToken.trim() || qrRedeemMutation.isPending}
                className="btn-primary w-full py-2.5 text-sm"
              >
                {qrRedeemMutation.isPending ? 'Confirming…' : 'Confirm return via QR'}
              </button>
            </div>
          )}
        </section>

        {status.conversation_id && (
          <p className="text-center mt-6 text-sm">
            <Link to={`/messages/${status.conversation_id}`} className="text-brand-600 hover:underline">
              Open chat
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
