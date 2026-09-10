/**
 * Status message when the viewer has already submitted a claim on a found item.
 */
export default function ViewerClaimBanner({ viewerClaim, className = '' }) {
  if (!viewerClaim?.message) return null

  const tone = {
    pending_review: 'bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-900/20 dark:text-amber-200 dark:border-amber-800/50',
    called_to_collect: 'bg-sky-50 text-sky-900 border-sky-200 dark:bg-sky-900/20 dark:text-sky-200 dark:border-sky-800/50',
    verified: 'bg-emerald-50 text-emerald-900 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-200 dark:border-emerald-800/50',
    rejected: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700',
  }[viewerClaim.viewer_state] || 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700'

  return (
    <p className={`text-sm leading-snug rounded-xl border px-3 py-2.5 ${tone} ${className}`}>
      {viewerClaim.message}
    </p>
  )
}
