/**
 * Horizontally scrollable drop-point filter chips (supervisor — all breakpoints).
 */
export default function DropPointChipRow({ dropPoints, value, onChange }) {
  if (!dropPoints?.length) return null
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 max-h-12 items-center scrollbar-none">
      <button
        type="button"
        onClick={() => onChange('')}
        className={`shrink-0 h-9 px-3 rounded-full text-sm font-medium border transition-colors
          ${!value
            ? 'bg-brand-100 dark:bg-brand-900/50 border-brand-500 text-brand-700 dark:text-brand-200'
            : 'border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400'}`}
      >
        All
      </button>
      {dropPoints.map((dp) => (
        <button
          key={dp.id}
          type="button"
          onClick={() => onChange(dp.id)}
          className={`shrink-0 h-9 px-3 rounded-full text-sm font-medium border transition-colors
            ${value === dp.id
              ? 'bg-brand-100 dark:bg-brand-900/50 border-brand-500 text-brand-700 dark:text-brand-200'
              : 'border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400'}`}
        >
          {dp.name}
        </button>
      ))}
    </div>
  )
}
