/**
 * Physical presence confirmation before verify/reject (V5).
 */
export const PHYSICAL_PRESENCE_WARNING =
  'Claimant must be physically present and thoroughly questioned before clicking this button'

export const PHYSICAL_PRESENCE_REJECT_WARNING =
  'Claimant must be physically present and thoroughly questioned before rejection'

export default function PhysicalPresenceDialog({
  open,
  kind,
  onConfirm,
  onWait,
}) {
  if (!open) return null

  const isVerify = kind === 'verify'
  const title = isVerify ? 'Confirm physical verification' : 'Confirm rejection decision'
  const question = isVerify
    ? 'Is the claimant physically present at the drop point and have they been thoroughly questioned about this item?'
    : 'Was the claimant physically present at the drop point and thoroughly questioned before this decision?'
  const confirmLabel = isVerify ? 'Yes — Proceed with Verification' : 'Yes — Confirm Rejection'
  const waitLabel = 'No — Wait for Claimant'

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="physical-presence-title"
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-4"
      >
        <h2 id="physical-presence-title" className="text-lg font-semibold text-slate-100">
          {title}
        </h2>
        <p className="text-sm text-slate-300 leading-relaxed">{question}</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end pt-2">
          <button
            type="button"
            onClick={onWait}
            className="btn-secondary text-sm py-2.5 order-2 sm:order-1"
          >
            {waitLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`text-sm py-2.5 rounded-xl font-semibold order-1 sm:order-2 ${
              isVerify
                ? 'btn-primary'
                : 'border border-red-800 text-red-300 hover:bg-red-900/30'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
