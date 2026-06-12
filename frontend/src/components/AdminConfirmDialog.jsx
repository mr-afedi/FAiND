/**
 * Confirmation dialog for destructive admin actions (Section 27.19).
 */
export default function AdminConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
  loading = false,
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-md rounded-2xl border border-slate-700
                   bg-slate-900 p-5 shadow-xl"
      >
        <h3 className="text-base font-semibold text-slate-100">{title}</h3>
        {description && (
          <p className="text-sm text-slate-400 mt-2 whitespace-pre-wrap">{description}</p>
        )}
        <div className="flex justify-end gap-2 mt-5">
          <button
            type="button"
            className="btn-secondary text-xs py-2 px-4"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`text-xs py-2 px-4 rounded-lg font-medium ${
              destructive
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'btn-primary'
            }`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
