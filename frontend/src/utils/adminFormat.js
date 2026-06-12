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
  claims: 'No claims awaiting review — all caught up!',
  disputes: 'No open disputes — queue is clear.',
  reports: 'No pending reports — nothing to review.',
  fraud: 'No fraud alerts above threshold.',
  posts: 'No active posts match your filters.',
  users: 'No users match your search.',
  logs: 'No admin log entries match your filters.',
  returned: 'No returned items match your filters.',
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
  promote_admin: 'Promoted to assistant admin',
  demote_admin: 'Demoted from assistant admin',
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
  confirm_fraud: 'Fraud confirmed',
  clear_fraud_flag: 'Fraud flag cleared',
  allow_verification: 'Verification allowed',
  request_more_info: 'More info requested',
  trust_adjustment: 'Trust adjustment',
  lock_item: 'Item locked',
  escalate_dispute: 'Dispute escalated',
  open_manual_dispute: 'Manual dispute opened',
}

const TARGET_TYPE_LABELS = {
  user: 'User',
  item: 'Post',
  potential_match: 'Claim',
  item_return: 'Return',
  dispute: 'Dispute',
  post_report: 'Post report',
  user_report: 'User report',
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

const FRAUD_SIGNAL_LABELS = {
  failed_verifications_2_in_24h: '2 failed verifications in 24h',
  failed_verifications_3_in_24h: '3 failed verifications in 24h',
  repeated_low_score_multi_item: 'Repeated low-score claims',
  path_b_c_claim_failed: 'Path B/C claim failed',
  unusual_claim_volume: 'Unusual claim volume',
  user_report_received: 'User report received',
  admin_confirmed_fraud: 'Admin confirmed fraud',
  admin_cleared_flag: 'Admin cleared flag',
  admin_verification_override: 'Verification override granted',
  gradual_improvement: 'Gradual score improvement',
  risk_tier_high: 'Risk tier crossed to high',
  dispute_user_flagged: 'Flagged in dispute resolution',
}

export function formatFraudSignal(signal) {
  return FRAUD_SIGNAL_LABELS[signal] || (signal || '').replace(/_/g, ' ')
}

export function formatAdminLogDetail(log) {
  const { action, detail = {} } = log
  if (!detail || Object.keys(detail).length === 0) return null

  switch (action) {
    case 'trust_adjustment': {
      const { delta, reason, trust_before, trust_after } = detail
      const change = scoreChange(trust_before, trust_after)
      const parts = []
      if (change) {
        parts.push(`Trust score changed from ${trust_before} to ${trust_after} (${signedDelta(delta)}).`)
      } else if (delta != null) {
        parts.push(`Trust score adjusted by ${signedDelta(delta)}.`)
      }
      if (reason) parts.push(`Reason: ${reason}`)
      return parts.join(' ')
    }
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
    case 'confirm_fraud':
    case 'clear_fraud_flag':
      return scoreChange(detail.fraud_risk_before, detail.fraud_risk_after)
        ? `Fraud risk ${detail.fraud_risk_before} → ${detail.fraud_risk_after}.`
        : null
    case 'allow_verification':
      return 'Verification override enabled for this user.'
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
