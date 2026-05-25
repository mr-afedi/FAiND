/**
 * Compact category filter tiles (browse /lost /found) — all 9 visible, no scroll.
 */
import { CATEGORY_META } from './icons'

const entries = Object.entries(CATEGORY_META)

export default function CategoryFilterGrid({ selected = [], onToggle }) {
  return (
    <div
      className="grid grid-cols-3 gap-1 w-[13.5rem]"
      role="group"
      aria-label="Filter by category"
    >
      {entries.map(([value, { Icon, label }]) => {
        const checked = selected.includes(value)
        const isBag = value === 'bag'
        return (
          <button
            key={value}
            type="button"
            aria-pressed={checked}
            title={label}
            onClick={() => onToggle(value)}
            className={`flex flex-col items-center justify-center gap-0.5 rounded-lg
                        px-1 py-1.5 text-center transition-colors duration-100
                        focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500
                        ${checked
                          ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-500/60 dark:bg-brand-900/35 dark:text-brand-300 dark:ring-brand-500/50'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60'}`}
          >
            <Icon
              className={`shrink-0 ${isBag ? 'w-3.5 h-3.5' : 'w-3.5 h-3.5'}`}
              strokeWidth={isBag ? 2.25 : 1.75}
              aria-hidden
            />
            <span className="text-[9px] font-medium leading-tight line-clamp-2 w-full">
              {label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
