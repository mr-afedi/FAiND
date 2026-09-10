/**
 * Camera QR scanner for authority drop-off confirmation (Section 9.2).
 * Uses native BarcodeDetector when available; manual entry always available.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'

export default function AuthorityQrScanner({ onScan, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)
  const scannedRef = useRef(false)
  const [error, setError] = useState(null)
  const [manualToken, setManualToken] = useState('')
  const [supportsDetector, setSupportsDetector] = useState(false)

  const stopCamera = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  const submitToken = useCallback((value) => {
    const token = value.trim()
    if (!token || scannedRef.current) return
    scannedRef.current = true
    onScan(token)
    window.setTimeout(() => { scannedRef.current = false }, 2500)
  }, [onScan])

  useEffect(() => {
    let active = true
    scannedRef.current = false

    const hasDetector = typeof window !== 'undefined' && 'BarcodeDetector' in window
    setSupportsDetector(hasDetector)

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' } },
          audio: false,
        })
        if (!active) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        const video = videoRef.current
        if (!video) return
        video.srcObject = stream
        await video.play()

        if (!hasDetector) {
          setError('Camera ready — enter the QR code manually below if auto-scan is unavailable.')
          return
        }

        let detector
        try {
          detector = new window.BarcodeDetector({ formats: ['qr_code'] })
        } catch {
          try {
            detector = new window.BarcodeDetector({ formats: ['qr'] })
          } catch {
            detector = new window.BarcodeDetector()
          }
        }

        const tick = async () => {
          if (!active || scannedRef.current || !videoRef.current) return
          try {
            const codes = await detector.detect(videoRef.current)
            if (codes.length > 0 && codes[0].rawValue) {
              submitToken(codes[0].rawValue)
              return
            }
          } catch {
            // ignore frame errors
          }
          rafRef.current = requestAnimationFrame(tick)
        }
        rafRef.current = requestAnimationFrame(tick)
      } catch (err) {
        if (active) {
          setError(err?.message || 'Could not access camera. Use manual entry below.')
        }
      }
    }

    start()
    return () => {
      active = false
      stopCamera()
    }
  }, [submitToken, stopCamera])

  function handleManualSubmit(e) {
    e.preventDefault()
    submitToken(manualToken)
  }

  return createPortal(
    <div className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-4">
      <div className="glass w-full max-w-md p-5 space-y-4 bg-white dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Scan drop-off QR</h2>
          <button
            type="button"
            onClick={() => { stopCamera(); onClose() }}
            className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-200"
          >
            Close
          </button>
        </div>

        <div className="relative w-full overflow-hidden rounded-xl bg-black aspect-square max-h-72">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            playsInline
            muted
            autoPlay
          />
          <div className="pointer-events-none absolute inset-8 border-2 border-brand-400/70 rounded-lg" />
        </div>

        {error && (
          <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <form onSubmit={handleManualSubmit} className="space-y-2">
          <label className="label text-slate-700 dark:text-slate-300">
            QR payload {supportsDetector ? '(manual fallback)' : '(required)'}
          </label>
          <input
            type="text"
            className="input-field w-full text-sm font-mono"
            value={manualToken}
            onChange={(e) => setManualToken(e.target.value)}
            placeholder="faind-drop:…"
            autoComplete="off"
            spellCheck={false}
          />
          <button type="submit" className="btn-primary w-full text-sm min-h-[48px]">
            Confirm code
          </button>
        </form>

        <p className="text-xs text-slate-500 text-center">
          Point the camera at the finder&apos;s QR code on their tracking page.
        </p>
      </div>
    </div>,
    document.body
  )
}
