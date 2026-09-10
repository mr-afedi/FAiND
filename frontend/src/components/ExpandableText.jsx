/**
 * Inline "Read more / Show less" for text that exceeds two lines.
 */
import { useState, useRef, useEffect } from 'react'

export default function ExpandableText({
  text,
  className = '',
  buttonClassName = 'text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline mt-1',
}) {
  const [expanded, setExpanded] = useState(false)
  const [canExpand, setCanExpand] = useState(false)
  const bodyRef = useRef(null)

  useEffect(() => {
    const el = bodyRef.current
    if (!el || !text) {
      setCanExpand(false)
      return
    }
    const measure = () => {
      setCanExpand(el.scrollHeight > el.clientHeight + 1)
    }
    measure()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    ro?.observe(el)
    return () => ro?.disconnect()
  }, [text])

  if (!text) return null

  return (
    <>
      <p
        ref={bodyRef}
        className={`${className} ${expanded ? '' : 'line-clamp-2'}`}
      >
        {text}
      </p>
      {canExpand && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded((v) => !v)
          }}
          className={buttonClassName}
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}
    </>
  )
}
