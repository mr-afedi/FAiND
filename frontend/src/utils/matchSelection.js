/**
 * Pick the most relevant match when multiple exist for the same item.
 * Verified matches take priority over active ones so users are not re-prompted.
 */
const STATUS_RANK = {
  verified: 0,
  pending_review: 1,
  paused: 2,
  active: 3,
  expired: 9,
}

export function pickPrimaryMatch(matches, predicate) {
  const candidates = (matches || []).filter(predicate)
  if (!candidates.length) return null
  return [...candidates].sort((a, b) => {
    const ra = STATUS_RANK[a.status] ?? 5
    const rb = STATUS_RANK[b.status] ?? 5
    if (ra !== rb) return ra - rb
    return (b.match_score || 0) - (a.match_score || 0)
  })[0]
}

function isClaimBridgeMatch(match) {
  const path = match?.score_breakdown?.path
  return path === 'path_b' || path === 'path_c'
}

export function matchNeedsVerification(match) {
  return match?.status === 'active' && !isClaimBridgeMatch(match)
}

export function matchVerificationComplete(match) {
  return match?.status === 'verified' || Boolean(match?.conversation_id)
}
