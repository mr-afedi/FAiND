/**
 * V5 item status labels and pill styles — shared across browse, detail, dashboard.
 */

export const ITEM_STATUS_PILL = {
  open:                'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  found:               'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  overdue:             'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  unconfirmed:         'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400',
  at_droppoint:        'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  under_claim_review:  'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  potential_match:     'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  under_verification:  'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  under_dispute:       'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  returned:            'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  expired:             'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  archived:            'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
  closed:              'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
}

export function formatItemStatus(status) {
  if (!status) return ''
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function statusPillClass(status) {
  return ITEM_STATUS_PILL[status] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
}
