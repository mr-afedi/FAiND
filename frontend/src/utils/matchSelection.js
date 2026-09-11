/**
 * Pick the most relevant match when multiple exist for the same item.
 * Verified matches take priority over active ones.
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

export function matchNeedsVerification(match) {
  return false
}

/** Path A — lost owner can submit a claim when match is active. */
export function matchCanSubmitClaim(match) {
  return match?.user_role === 'lost_owner'
    && (match?.status === 'active' || match?.status === 'pending_review')
}

/** Legacy return flow — kept for verified matches with existing returns. */
export function matchCanConfirmReturn(match) {
  return match?.status === 'verified'
}

export function matchVerificationComplete(match) {
  return matchCanConfirmReturn(match)
}
