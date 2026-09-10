/**
 * Centered detail modal for staff dashboards (desktop only, min-width 768px).
 */
import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function StaffDesktopDetailModal({
  open,
  onClose,
  title,
  children,
  footer,
}) {
  useEffect(() => {
    if (!open) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  if (!open) return null

  return (
    <div className="hidden md:flex fixed inset-0 z-[60] items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-label="Close backdrop"
      />

      <div
        className="relative flex flex-col bg-white dark:bg-slate-950 rounded-2xl
                   border border-slate-200 dark:border-slate-800 shadow-2xl
                   w-[85vw] h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Details'}
      >
        <div className="flex items-start justify-between gap-3 px-6 pt-5 pb-3 shrink-0
                        border-b border-slate-200 dark:border-slate-800">
          {title ? (
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-snug pr-2">
              {title}
            </h2>
          ) : (
            <span />
          )}
          <button
            type="button"
            onClick={onClose}
            className="w-10 h-10 shrink-0 flex items-center justify-center rounded-xl
                       text-slate-600 dark:text-slate-300
                       hover:bg-slate-100 dark:hover:bg-slate-800
                       border border-slate-300 dark:border-slate-600"
            aria-label="Close"
          >
            <X className="w-5 h-5" aria-hidden />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-6 py-4 min-h-0">
          {children}
        </div>

        {footer && (
          <div className="shrink-0 border-t border-slate-200 dark:border-slate-800
                          bg-white dark:bg-slate-950 px-6 py-4 space-y-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
