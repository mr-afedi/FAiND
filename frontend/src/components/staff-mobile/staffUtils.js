export function timeSincePosted(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

/** Returns green | amber | red for drop-off deadline display. */
export function dropoffCountdownTone(item) {
  if (item.status === 'overdue' || item.dropoff_phase === 'unconfirmed') return 'red'
  if (item.dropoff_phase === 'finder_confirmed') return 'amber'
  if (item.dropoff_hours_remaining > 24) return 'green'
  if (item.dropoff_hours_remaining > 0) return 'amber'
  if (item.dropoff_hours_until_unconfirmed > 0) return 'amber'
  return 'red'
}

export function dropoffCountdownLabel(item) {
  if (item.dropoff_phase === 'finder_confirmed') {
    return 'Finder marked drop-off — awaiting your receipt'
  }
  if (item.dropoff_hours_remaining > 0) {
    const h = item.dropoff_hours_remaining
    return `${h} hour${h !== 1 ? 's' : ''} left in 48h window`
  }
  if (item.dropoff_hours_until_unconfirmed > 0) {
    const h = item.dropoff_hours_until_unconfirmed
    return `Past 48h — ${h}h grace period remaining`
  }
  if (item.status === 'overdue' || item.dropoff_phase === 'overdue') return 'Overdue'
  return 'Deadline passed'
}

const TONE_STYLES = {
  green: 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950/50 dark:border-emerald-700/60 dark:text-emerald-200',
  amber: 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/50 dark:border-amber-700/60 dark:text-amber-200',
  red: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950/50 dark:border-red-800/60 dark:text-red-200',
}

export function countdownClassName(tone) {
  return TONE_STYLES[tone] || TONE_STYLES.amber
}
