/**
 * Category dropdown for report forms — icon + label per row, no scroll.
 * In-page absolute menu (scrolls with the form). Parent section uses
 * `relative z-[1] overflow-visible` so the list clears the next card.
 */
import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import { CATEGORY_META } from './icons'

const entries = Object.entries(CATEGORY_META)

export default function CategoryPicker({
  value,
  onChange,
  className = '',
  placeholder = 'Select a category…',
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const selected = value ? CATEGORY_META[value] : null

  function pick(catValue) {
    onChange(catValue)
    setOpen(false)
  }

  return (
    <div ref={ref} className={`relative w-full ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="input-field w-full flex items-center gap-2.5 text-left py-2.5 pr-9 relative"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={selected ? `Category: ${selected.label}` : placeholder}
      >
        {selected ? (
          <>
            <CategoryOptionIcon category={value} />
            <span className="flex-1 truncate text-sm text-slate-900 dark:text-slate-100">
              {selected.label}
            </span>
          </>
        ) : (
          <span className="flex-1 text-sm text-slate-400 dark:text-slate-500">{placeholder}</span>
        )}
        <ChevronDown
          className={`absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 shrink-0
                      text-slate-400 transition-transform duration-150
                      ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Item category"
          className="absolute z-50 mt-1 w-full rounded-xl border border-slate-200 dark:border-slate-700
                     bg-white dark:bg-slate-800 shadow-lg py-1.5"
        >
          {entries.map(([catValue, { label }]) => {
            const isSelected = value === catValue
            return (
              <li key={catValue} role="option" aria-selected={isSelected}>
                <button
                  type="button"
                  onClick={() => pick(catValue)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left
                              transition-colors duration-100
                              ${isSelected
                                ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                                : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/60'}`}
                >
                  <CategoryOptionIcon category={catValue} />
                  <span className="flex-1 truncate">{label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function CategoryOptionIcon({ category }) {
  const { Icon } = CATEGORY_META[category] ?? CATEGORY_META.other
  const isBag = category === 'bag'

  return (
    <Icon
      className="w-4 h-4 shrink-0 text-slate-500 dark:text-slate-400"
      strokeWidth={isBag ? 2.25 : 1.75}
      aria-hidden
    />
  )
}
