/**
 * Embedded finder drop-off tracking on item detail (Section 7.3–7.5).
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  confirmFoundDropOffByItemId,
  confirmFoundDropOffByTrackingRef,
} from '../services/itemService'
import { saveEscrowToken } from '../utils/tokenEscrow'
import { invalidateAfterDropOff } from '../utils/queryCache'

function phaseLabel(phase) {
  if (phase === 'overdue') return 'Overdue'
  if (phase === 'finder_confirmed') return 'Awaiting drop point receipt'
  if (phase === 'at_droppoint') return 'At Drop Point'
  return 'Pending Drop-Off'
}

export default function FinderDropOffSection({
  itemId,
  trackingRef,
  trackData,
  dropPointName,
  onUpdated,
}) {
  const queryClient = useQueryClient()
  const dropOff = trackData?.drop_off || {}
  const qrImgUrl = dropOff.qr_payload
    ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(dropOff.qr_payload)}`
    : null
  const resolvedDropPoint = dropPointName || trackData?.drop_point_name || 'the drop point'

  const { mutate: confirmDropOff, isPending } = useMutation({
    mutationFn: () => (
      trackingRef
        ? confirmFoundDropOffByTrackingRef(trackingRef)
        : confirmFoundDropOffByItemId(itemId)
    ),
    onSuccess: (data) => {
      if (data.token_escrow?.escrow_token) {
        saveEscrowToken(data.token_escrow.escrow_token)
      }
      invalidateAfterDropOff(queryClient, { itemId, trackingRef })
      onUpdated?.(data.item)
      toast.success(data.message)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Could not confirm drop-off'),
  })

  if (dropOff.dropoff_phase === 'at_droppoint' || trackData?.status === 'at_droppoint') {
    return (
      <div className="mb-6 rounded-2xl border border-emerald-200/70 dark:border-emerald-800/50
                      bg-emerald-50/80 dark:bg-emerald-950/30 px-4 py-3">
        <p className="text-sm text-emerald-800 dark:text-emerald-200">
          Item is at <strong>{resolvedDropPoint}</strong> — awaiting collection by the owner.
        </p>
      </div>
    )
  }

  if (dropOff.dropoff_phase === 'unconfirmed') {
    return (
      <div className="mb-6 rounded-2xl border border-red-200/70 dark:border-red-900/50
                      bg-red-50/60 dark:bg-red-950/20 px-4 py-3">
        <p className="text-sm font-semibold text-red-700 dark:text-red-300">
          No longer accepting drop-off
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          The 72-hour window has passed without confirmation.
        </p>
      </div>
    )
  }

  return (
    <div className="mb-6 glass p-5 space-y-4 border border-brand-200/50 dark:border-brand-800/40">
      <div>
        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100">
          Track Drop-Off Status
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Drop point: {resolvedDropPoint}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full
                         bg-brand-100 text-brand-800 dark:bg-brand-900/40 dark:text-brand-200">
          {phaseLabel(dropOff.dropoff_phase)}
        </span>
        {dropOff.dropoff_phase === 'overdue' && (
          <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full
                           bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            Overdue
          </span>
        )}
      </div>

      {dropOff.hours_remaining > 0 ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          <strong className="text-slate-800 dark:text-slate-100">{dropOff.hours_remaining}</strong>
          {' '}hour{dropOff.hours_remaining !== 1 ? 's' : ''} remaining in the 48-hour on-time window.
        </p>
      ) : dropOff.hours_until_unconfirmed > 0 ? (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Past the 48-hour on-time window — you can still drop off for{' '}
          <strong>{dropOff.hours_until_unconfirmed}</strong> more hour
          {dropOff.hours_until_unconfirmed !== 1 ? 's' : ''}.
        </p>
      ) : null}

      {qrImgUrl && (
        <div className="text-center">
          <p className="text-xs text-slate-500 mb-2">Show this QR code at the drop point</p>
          <img
            src={qrImgUrl}
            alt="Drop-off QR code"
            className="mx-auto rounded-lg border border-slate-200 dark:border-slate-700"
            width={200}
            height={200}
          />
        </div>
      )}

      {dropOff.can_confirm_drop_off && (
        <button
          type="button"
          onClick={() => confirmDropOff()}
          disabled={isPending}
          className="btn-primary w-full sm:w-auto text-sm"
        >
          {isPending ? 'Confirming…' : 'I Dropped This Off'}
        </button>
      )}

      {dropOff.finder_dropped_off_at && !dropOff.authority_received_at && (
        <p className="text-xs text-slate-500">
          You marked this as dropped off. Waiting for the drop point to confirm receipt.
        </p>
      )}
    </div>
  )
}
