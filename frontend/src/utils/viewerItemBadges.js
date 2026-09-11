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

const PATH_B_BADGE = {
  under_review: 'Your claim is under admin review',
  approved: 'Your claim was approved — chat is open',
  rejected: 'Claim not approved',
  exhausted: 'You have reached the maximum number of attempts for this item',
}

const PATH_C_BADGE = {
  under_review: 'Your claim is under admin review',
  approved: 'Your claim was approved — chat is open',
  rejected: 'Claim not approved',
  exhausted: 'You have reached the maximum number of attempts for this item',
}

export function getViewerBadge(item, userId, matches, scope = {}) {
  if (!userId || !item?.id) return null

  const { homepage = false, browse = false } = scope
  const itemId = item.id
  const isLost = item.item_type === 'lost'
  const isFound = item.item_type === 'found'
  const isOwner = idEq(item.posted_by?.id, userId)

  // Path B claim state from API (homepage + browse + detail cards)
  if (isLost && !isOwner && item.viewer_path_b_status) {
    return PATH_B_BADGE[item.viewer_path_b_status] || null
  }

  // Path C claim state from API
  if (isFound && !isOwner && item.viewer_path_c_status) {
    return PATH_C_BADGE[item.viewer_path_c_status] || null
  }

  // Chat unlocked — homepage + browse: own item and matched peer item
  if (homepage || browse) {
    if (item.viewer_chat_unlocked) return 'Chat Opened'
    if (matches?.length) {
      const chatOpen = matches.some(
        (m) => matchChatUnlocked(m)
          && (idEq(m.lost_item?.id, itemId) || idEq(m.found_item?.id, itemId)),
      )
      if (chatOpen) return 'Chat Opened'
    }
  }

  if (!matches?.length) return null

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
