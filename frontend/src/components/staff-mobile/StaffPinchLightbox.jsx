/**
 * Pinch-to-zoom fullscreen lightbox for staff dashboards.
 */
import { useState, useRef, useCallback } from 'react'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'
import { optimizeCloudinaryUrl } from '../../utils/cloudinary'

export default function StaffPinchLightbox({ images, startIdx = 0, onClose }) {
  const [idx, setIdx] = useState(startIdx)
  const [scale, setScale] = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })
  const touchStartX = useRef(null)
  const pinchStartDist = useRef(null)
  const pinchStartScale = useRef(1)
  const lastPan = useRef({ x: 0, y: 0 })
  const panStart = useRef(null)

  const urls = (images || []).map((u) => optimizeCloudinaryUrl(u))
  if (!urls.length) return null

  const resetZoom = useCallback(() => {
    setScale(1)
    setTranslate({ x: 0, y: 0 })
  }, [])

  function goPrev(e) {
    e?.stopPropagation()
    resetZoom()
    setIdx((i) => Math.max(0, i - 1))
  }

  function goNext(e) {
    e?.stopPropagation()
    resetZoom()
    setIdx((i) => Math.min(urls.length - 1, i + 1))
  }

  function dist(t1, t2) {
    const dx = t1.clientX - t2.clientX
    const dy = t1.clientY - t2.clientY
    return Math.hypot(dx, dy)
  }

  function onTouchStart(e) {
    if (e.touches.length === 2) {
      pinchStartDist.current = dist(e.touches[0], e.touches[1])
      pinchStartScale.current = scale
      touchStartX.current = null
      return
    }
    if (e.touches.length === 1) {
      if (scale > 1) {
        panStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
        lastPan.current = { ...translate }
      } else {
        touchStartX.current = e.touches[0].clientX
      }
    }
  }

  function onTouchMove(e) {
    if (e.touches.length === 2 && pinchStartDist.current) {
      const d = dist(e.touches[0], e.touches[1])
      const next = Math.min(4, Math.max(1, pinchStartScale.current * (d / pinchStartDist.current)))
      setScale(next)
      return
    }
    if (e.touches.length === 1 && scale > 1 && panStart.current) {
      const dx = e.touches[0].clientX - panStart.current.x
      const dy = e.touches[0].clientY - panStart.current.y
      setTranslate({ x: lastPan.current.x + dx, y: lastPan.current.y + dy })
    }
  }

  function onTouchEnd(e) {
    pinchStartDist.current = null
    panStart.current = null
    if (scale <= 1.05) resetZoom()
    if (touchStartX.current == null || scale > 1) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(dx) < 50) return
    if (dx > 0) goPrev()
    else goNext()
  }

  return (
    <div
      className="fixed inset-0 z-[70] bg-black flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label="Image viewer"
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 z-20 w-12 h-12 flex items-center justify-center
                   rounded-full bg-white/15 text-white hover:bg-white/25"
        aria-label="Close"
      >
        <X className="w-6 h-6" strokeWidth={2} aria-hidden />
      </button>

      <div
        className="w-full h-full flex items-center justify-center overflow-hidden touch-none"
        onClick={onClose}
      >
        <img
          src={urls[idx]}
          alt=""
          onClick={(e) => e.stopPropagation()}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          style={{
            transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
            transition: pinchStartDist.current ? 'none' : 'transform 0.15s ease-out',
          }}
          className="max-w-full max-h-full object-contain select-none"
          draggable={false}
        />
      </div>

      {urls.length > 1 && scale <= 1 && (
        <>
          {idx > 0 && (
            <button
              type="button"
              onClick={goPrev}
              className="absolute left-3 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                         bg-white/10 text-white flex items-center justify-center"
              aria-label="Previous"
            >
              <ChevronLeft className="w-6 h-6" aria-hidden />
            </button>
          )}
          {idx < urls.length - 1 && (
            <button
              type="button"
              onClick={goNext}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                         bg-white/10 text-white flex items-center justify-center"
              aria-label="Next"
            >
              <ChevronRight className="w-6 h-6" aria-hidden />
            </button>
          )}
          <p className="absolute bottom-6 left-0 right-0 text-center text-sm text-white/70">
            {idx + 1} / {urls.length}
          </p>
        </>
      )}
    </div>
  )
}
