export function formatClaimWhen(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function claimStatusBadge(status) {
  const styles = {
    pending: 'bg-amber-900/40 text-amber-200',
    verified: 'bg-emerald-900/40 text-emerald-200',
    rejected: 'bg-slate-700 text-slate-400',
  }
  return styles[status] || 'bg-slate-800 text-slate-300'
}
