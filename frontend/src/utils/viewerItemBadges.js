/**
 * Role-specific card badges (Bugs 3 & 4) — only for the viewing user.
 * @param {{ homepage?: boolean, browse?: boolean }} scope
 */

function idEq(a, b) {
  return String(a) === String(b)
}

/**
 * True when a verification was submitted and is still in progress
 * (admin review or lost item under verification) — not on match-created only.
 */
export function matchVerificationInProgress(match) {
  if (!match?.has_verification_attempt) return false
  return (
    match.status === 'pending_review'
    || match.lost_item?.status === 'under_verification'
  )
}

/** Verified match with unlocked chat (Path A approved). */
export function matchChatUnlocked(match) {
  return Boolean(
    match?.status === 'verified' && match.conversation_id,
  )
}

export function getViewerBadge(item, userId, matches, scope = {}) {
  if (!userId || !item?.id || !matches?.length) return null

  const { homepage = false, browse = false } = scope
  const itemId = item.id
  const isLost = item.item_type === 'lost'
  const isFound = item.item_type === 'found'
  const isOwner = idEq(item.posted_by?.id, userId)

  // Chat unlocked — homepage only, each party on their own item card
  if (homepage && isLost && isOwner) {
    const chatOpen = matches.some(
      (m) => m.user_role === 'lost_owner'
        && idEq(m.lost_item?.id, itemId)
        && matchChatUnlocked(m),
    )
    if (chatOpen) return 'Chat Opened'
  }
  if (homepage && isFound && isOwner) {
    const chatOpen = matches.some(
      (m) => m.user_role === 'found_owner'
        && idEq(m.found_item?.id, itemId)
        && matchChatUnlocked(m),
    )
    if (chatOpen) return 'Chat Opened'
  }

  // User A — own lost item (homepage only); after User A submits verification
  if (homepage && isLost && isOwner) {
    const claimStarted = matches.some(
      (m) => m.user_role === 'lost_owner'
        && idEq(m.lost_item?.id, itemId)
        && matchVerificationInProgress(m),
    )
    if (claimStarted) return 'Ownership claim in progress'
  }

  // User A — matched found item they are claiming (homepage only)
  if (homepage && isFound && !isOwner) {
    const underReview = matches.some(
      (m) => m.user_role === 'lost_owner'
        && idEq(m.found_item?.id, itemId)
        && m.status === 'pending_review',
    )
    if (underReview) return 'Your claim is under review'
  }

  // User B — own found item with claims in admin review (homepage only)
  if (homepage && isFound && isOwner) {
    const claimCount = matches.filter(
      (m) => m.user_role === 'found_owner'
        && idEq(m.found_item?.id, itemId)
        && m.status === 'pending_review',
    ).length
    if (claimCount === 1) return '1 ownership claim under review'
    if (claimCount > 1) return `${claimCount} ownership claims under review`
  }

  // User B — matched lost item (homepage + browse); after a verification attempt
  if ((homepage || browse) && isLost && !isOwner) {
    const claiming = matches.some(
      (m) => m.user_role === 'found_owner'
        && idEq(m.lost_item?.id, itemId)
        && matchVerificationInProgress(m),
    )
    if (claiming) return 'Someone is claiming this item'
  }

  return null
}
