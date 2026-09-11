/**
 * Full-screen bottom sheet for staff dashboard detail views (mobile only).
 */
import { useRef, useState, useEffect } from 'react'
import { X } from 'lucide-react'

export default function StaffMobileBottomSheet({
  open,
  onClose,
  title,
  children,
  footer,
}) {
  const [dragOffset, setDragOffset] = useState(0)
  const startY = useRef(null)
  const dragging = useRef(false)

  useEffect(() => {
    if (!open) setDragOffset(0)
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [open])

  if (!open) return null

  function onTouchStart(e) {
    startY.current = e.touches[0].clientY
    dragging.current = true
  }

  function onTouchMove(e) {
    if (!dragging.current || startY.current == null) return
    const dy = e.touches[0].clientY - startY.current
    if (dy > 0) setDragOffset(dy)
  }

  function onTouchEnd() {
    if (dragOffset > 120) onClose()
    setDragOffset(0)
    dragging.current = false
    startY.current = null
  }

  return (
    <div className="md:hidden fixed inset-0 z-[55] flex flex-col justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        aria-label="Close"
      />

      <div
        className="relative flex flex-col bg-slate-950 rounded-t-2xl border-t border-slate-800
                   max-h-[92vh] min-h-[50vh] transition-transform"
        style={{ transform: dragOffset ? `translateY(${dragOffset}px)` : undefined }}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Details'}
      >
        <div
          className="flex justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing touch-none"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          <div className="w-10 h-1 rounded-full bg-slate-600" aria-hidden />
        </div>

        {title && (
          <div className="flex items-center justify-between gap-3 px-4 pb-3 shrink-0">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-snug">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="w-11 h-11 shrink-0 flex items-center justify-center rounded-xl
                         text-slate-400 hover:bg-slate-800"
              aria-label="Close"
            >
              <X className="w-5 h-5" aria-hidden />
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 pb-4 text-base leading-relaxed">
          {children}
        </div>

        {footer && (
          <div className="shrink-0 border-t border-slate-800 bg-slate-950 px-4 py-4
                          pb-[max(1rem,env(safe-area-inset-bottom))] space-y-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
