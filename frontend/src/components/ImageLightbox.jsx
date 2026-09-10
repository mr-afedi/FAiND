/**
 * Fullscreen image viewer — tap thumbnails to open; swipe between images.
 */
import { useState, useRef } from 'react'
import { X, ChevronLeft, ChevronRight } from './icons'

export default function ImageLightbox({ images, startIdx = 0, onClose }) {
  const [idx, setIdx] = useState(startIdx)
  const touchStartX = useRef(null)

  if (!images?.length) return null

  function goPrev(e) {
    e?.stopPropagation()
    setIdx((i) => Math.max(0, i - 1))
  }

  function goNext(e) {
    e?.stopPropagation()
    setIdx((i) => Math.min(images.length - 1, i + 1))
  }

  function onTouchStart(e) {
    touchStartX.current = e.touches[0].clientX
  }

  function onTouchEnd(e) {
    if (touchStartX.current == null) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(dx) < 50) return
    if (dx > 0) goPrev()
    else goNext()
  }

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Image viewer"
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl
                   w-10 h-10 flex items-center justify-center rounded-full
                   bg-white/10 hover:bg-white/20 transition-colors z-10"
        aria-label="Close"
      >
        <X className="w-5 h-5" aria-hidden />
      </button>

      <img
        src={images[idx]}
        alt=""
        onClick={(e) => e.stopPropagation()}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        className="max-w-[90vw] max-h-[90vh] object-contain rounded-xl shadow-2xl select-none"
        draggable={false}
      />

      {images.length > 1 && (
        <>
          <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-3">
            {images.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={(e) => { e.stopPropagation(); setIdx(i) }}
                className={`w-2.5 h-2.5 rounded-full transition-all ${
                  i === idx ? 'bg-white scale-125' : 'bg-white/40 hover:bg-white/70'
                }`}
                aria-label={`Image ${i + 1} of ${images.length}`}
              />
            ))}
          </div>
          {idx > 0 && (
            <button
              type="button"
              onClick={goPrev}
              className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                         bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              aria-label="Previous image"
            >
              <ChevronLeft className="w-5 h-5" aria-hidden />
            </button>
          )}
          {idx < images.length - 1 && (
            <button
              type="button"
              onClick={goNext}
              className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full
                         bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
              aria-label="Next image"
            >
              <ChevronRight className="w-5 h-5" aria-hidden />
            </button>
          )}
        </>
      )}
    </div>
  )
}

export function LightboxImage({
  src,
  images,
  index = 0,
  className = '',
  onOpen,
}) {
  const gallery = images?.length ? images : [src]

  return (
    <button
      type="button"
      onClick={() => onOpen?.(gallery, index)}
      className={`p-0 border-0 bg-transparent cursor-zoom-in ${className}`}
    >
      <img src={src} alt="" className="w-full h-full object-cover pointer-events-none" />
    </button>
  )
}
