/** Admin dashboard formatting — scores as %, status colors (Feature R). */

export function formatScorePct(score) {
  if (score == null || Number.isNaN(Number(score))) return '—'
  return `${(Number(score) * 100).toFixed(1)}%`
}

export function statusColor(kind) {
  const map = {
    approved: 'text-emerald-400',
    verified: 'text-emerald-400',
    resolved: 'text-emerald-400',
    active: 'text-emerald-400',
    rejected: 'text-red-400',
    suspended: 'text-red-400',
    blocked: 'text-red-400',
    pending_review: 'text-amber-400',
    pending: 'text-amber-400',
    elevated: 'text-amber-400',
    under_dispute: 'text-amber-400',
    paused: 'text-amber-400',
    high: 'text-red-400',
  }
  return map[kind] || 'text-slate-400'
}

export function riskTierColor(tier) {
  const t = (tier || '').toLowerCase()
  if (t === 'blocked' || t === 'high') return 'text-red-400 bg-red-500/10'
  if (t === 'elevated') return 'text-amber-400 bg-amber-500/10'
  return 'text-emerald-400 bg-emerald-500/10'
}

export function pathBadge(path) {
  const label = (path || '').replace('path_', '').toUpperCase()
  return label || '?'
}

export const EMPTY_STATES = {
  disputes: 'No open disputes — queue is clear.',
  reports: 'No pending reports — nothing to review.',
  posts: 'No active posts match your filters.',
  users: 'No users match your search.',
  logs: 'No admin log entries match your filters.',
  returned: 'No returned items match your filters.',
  claims: 'No claims on found items yet.',
  drop_points: 'No drop points configured.',
}

export const ITEM_CATEGORIES = [
  'electronics', 'bag', 'id_card', 'keys', 'clothing',
  'books_notes', 'wallet', 'jewellery', 'other',
]

export function formatDateShort(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString()
}

const ADMIN_ACTION_LABELS = {
  promote_admin: 'Admin role changed',
  demote_admin: 'Admin role changed',
  suspend_user: 'User suspended',
  unsuspend_user: 'User unsuspended',
  approve_claim: 'Claim approved',
  reject_claim: 'Claim rejected',
  resolve_dispute: 'Dispute resolved',
  remove_post: 'Post removed',
  force_close_post: 'Post force-closed',
  dismiss_report: 'Report dismissed',
  warn_user: 'User warned',
  suppress_reporter: 'Reporter suppressed',
  request_more_info: 'More info requested',
  lock_item: 'Item locked',
  escalate_dispute: 'Dispute escalated',
  open_manual_dispute: 'Manual dispute opened',
  token_settings_update: 'Token settings updated',
  redemption_redeemed: 'Redemption code redeemed',
  drop_point_create: 'Drop point created',
  drop_point_update: 'Drop point updated',
  authority_create: 'Authority account created',
  authority_activate: 'Authority activated',
  authority_deactivate: 'Authority deactivated',
  authority_reassign: 'Authority reassigned',
  supervisor_create: 'Supervisor created',
  supervisor_update: 'Supervisor updated',
  handover_override: 'Handover completed (authority override)',
}

const TARGET_TYPE_LABELS = {
  user: 'User',
  item: 'Post',
  potential_match: 'Claim',
  item_return: 'Return',
  dispute: 'Dispute',
  post_report: 'Post report',
  user_report: 'User report',
  drop_point: 'Drop point',
  authority: 'Authority',
  supervisor: 'Supervisor',
  claim: 'Claim',
  handover: 'Handover',
  redemption_code: 'Redemption code',
  token_settings: 'Token settings',
}

function shortId(id) {
  if (!id) return ''
  const s = String(id)
  return s.length > 12 ? `${s.slice(0, 8)}…${s.slice(-4)}` : s
}

function signedDelta(delta) {
  const n = Number(delta)
  if (Number.isNaN(n)) return String(delta)
  return n > 0 ? `+${n}` : String(n)
}

function scoreChange(before, after) {
  if (before == null || after == null) return null
  return `${before} → ${after}`
}

export function formatAdminActionLabel(action) {
  return ADMIN_ACTION_LABELS[action] || (action || '').replace(/_/g, ' ')
}

export function formatAdminLogTarget(log) {
  const label = TARGET_TYPE_LABELS[log.target_type] || log.target_type?.replace(/_/g, ' ') || 'Target'
  const id = shortId(log.target_id)
  return id ? `${label} ${id}` : label
}

export function formatAdminLogDetail(log) {
  const { action, detail = {} } = log
  if (!detail || Object.keys(detail).length === 0) return null

  switch (action) {
    case 'approve_claim':
      return [
        detail.match_score != null && `Match score ${formatScorePct(detail.match_score)}.`,
        detail.status_before && detail.status_after
          && `Status ${detail.status_before.replace(/_/g, ' ')} → ${detail.status_after.replace(/_/g, ' ')}.`,
      ].filter(Boolean).join(' ') || null
    case 'reject_claim':
    case 'request_more_info':
      return detail.note ? `Note: ${detail.note}` : null
    case 'resolve_dispute':
      return [
        detail.dispute_type && `Type: ${detail.dispute_type.replace(/_/g, ' ')}.`,
        detail.outcome && `Outcome: ${detail.outcome.replace(/_/g, ' ')}.`,
        detail.note && `Note: ${detail.note}`,
        detail.winner_match_id && `Winning claim ${shortId(detail.winner_match_id)}.`,
      ].filter(Boolean).join(' ') || null
    case 'remove_post':
    case 'force_close_post':
      return [
        detail.reason && `Reason: ${detail.reason}`,
        detail.status_before && detail.status_after
          && `Status ${detail.status_before} → ${detail.status_after}.`,
      ].filter(Boolean).join(' ') || null
    case 'suspend_user':
      return detail.reason ? `Reason: ${detail.reason}` : 'Account suspended.'
    case 'unsuspend_user':
      return 'Account access restored.'
    case 'lock_item':
      return [
        detail.reason && `Reason: ${detail.reason}`,
        detail.locked_item_ids?.length
          && `${detail.locked_item_ids.length} item(s) locked.`,
      ].filter(Boolean).join(' ') || null
    case 'escalate_dispute':
      return [
        detail.dispute_type && `Type: ${detail.dispute_type}.`,
        detail.note && `Note: ${detail.note}`,
      ].filter(Boolean).join(' ') || null
    case 'open_manual_dispute':
      return detail.reason ? `Reason: ${detail.reason}` : null
    case 'dismiss_report':
    case 'warn_user':
      return [
        detail.action && `Action: ${detail.action.replace(/_/g, ' ')}.`,
        detail.status_before && detail.status_after
          && `Report ${detail.status_before} → ${detail.status_after}.`,
      ].filter(Boolean).join(' ') || null
    case 'suppress_reporter':
      return 'Reporter marked as bad faith; future reports deprioritized.'
    case 'token_settings_update':
      return Object.entries(detail)
        .map(([field, change]) => `${field.replace(/_/g, ' ')}: ${change.from} → ${change.to}`)
        .join(' · ') || null
    case 'redemption_redeemed':
      return [
        detail.code && `Code ${detail.code}.`,
        detail.token_amount != null && `${detail.token_amount} tokens.`,
        detail.supervisor_id && 'Redeemed by supervisor.',
      ].filter(Boolean).join(' ') || null
    case 'drop_point_create':
      return [
        detail.name && `Name: ${detail.name}.`,
        detail.type && `Type: ${detail.type}.`,
      ].filter(Boolean).join(' ') || null
    case 'drop_point_update':
      return Object.entries(detail)
        .map(([field, change]) => `${field}: ${change.from} → ${change.to}`)
        .join(' · ') || null
    case 'authority_create':
      return [
        detail.email && `Email: ${detail.email}.`,
        detail.drop_point_name && `Drop point: ${detail.drop_point_name}.`,
      ].filter(Boolean).join(' ') || null
    case 'authority_reassign':
      return [
        detail.from_drop_point_name && detail.to_drop_point_name
          && `${detail.from_drop_point_name} → ${detail.to_drop_point_name}.`,
      ].filter(Boolean).join(' ') || null
    case 'supervisor_create':
    case 'supervisor_update':
      return detail.email ? `Supervisor: ${detail.email}` : null
    case 'handover_override':
      return detail.note ? `Note: ${detail.note}` : null
    default:
      return Object.entries(detail)
        .map(([key, value]) => {
          const label = key.replace(/_/g, ' ')
          const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
          return `${label}: ${text}`
        })
        .join(' · ')
  }
}
