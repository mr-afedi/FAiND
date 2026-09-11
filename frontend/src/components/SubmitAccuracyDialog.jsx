/**
 * Accuracy confirmation before creating or claiming an item.
 */
export default function SubmitAccuracyDialog({ open, onConfirm, onEdit }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        onClick={onEdit}
        aria-label="Close"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-md rounded-2xl border border-slate-200 dark:border-slate-700
                   bg-white dark:bg-slate-900 p-6 shadow-2xl"
      >
        <p className="text-base font-semibold text-slate-900 dark:text-slate-100 leading-relaxed">
          Please confirm the information you provided is accurate.
        </p>
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-6">
          <button type="button" className="btn-secondary text-sm min-h-[44px]" onClick={onEdit}>
            Edit
          </button>
          <button type="button" className="btn-primary text-sm min-h-[44px]" onClick={onConfirm}>
            Yes, Submit
          </button>
        </div>
      </div>
    </div>
  )
}
