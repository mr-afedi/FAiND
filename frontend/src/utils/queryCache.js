/**
 * Shared React Query cache invalidation — call after mutations so UI refreshes
 * without a manual page reload.
 */
import { markPushPromptReady } from './pushPrompt'

/** After login, logout, or silent refresh bootstrap — refetch viewer-specific data. */
export function invalidateAfterAuthSession(queryClient) {
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  queryClient.invalidateQueries({ queryKey: ['me'] })
  queryClient.invalidateQueries({ queryKey: ['my-tokens'] })
}

export function invalidateAfterItemCreate(queryClient, { type = 'lost' } = {}) {
  queryClient.invalidateQueries({ queryKey: [type === 'lost' ? 'my-lost-items' : 'my-found-items'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  if (type === 'found') {
    queryClient.invalidateQueries({ queryKey: ['authority-incoming'] })
  }
}

export function invalidateAfterClaimSubmit(queryClient, { foundItemId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  queryClient.invalidateQueries({ queryKey: ['authority-claims-list'] })
  queryClient.invalidateQueries({ queryKey: ['supervisor-claims-list'] })
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
    queryClient.invalidateQueries({ queryKey: ['authority-claims', foundItemId] })
    queryClient.invalidateQueries({ queryKey: ['supervisor-claims', foundItemId] })
  }
}

export function invalidateAfterDropOff(queryClient, { itemId, trackingRef } = {}) {
  queryClient.invalidateQueries({ queryKey: ['authority-incoming'] })
  queryClient.invalidateQueries({ queryKey: ['authority-at-droppoint'] })
  if (itemId) {
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }
  if (trackingRef) {
    queryClient.invalidateQueries({ queryKey: ['found-track', trackingRef] })
  }
}

export function invalidateAfterAuthorityClaimAction(queryClient, { foundItemId, claimId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['authority-claims-list'] })
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
    queryClient.invalidateQueries({ queryKey: ['authority-claims', foundItemId] })
  }
  if (claimId) {
    queryClient.invalidateQueries({ queryKey: ['claim-status', claimId] })
  }
}

export function invalidateAfterHandover(queryClient, { handoverId, foundItemId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['authority-handover-queue'] })
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  queryClient.invalidateQueries({ queryKey: ['my-returns'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['public-returned'] })
  queryClient.invalidateQueries({ queryKey: ['admin-returned'] })
  if (handoverId) {
    queryClient.invalidateQueries({ queryKey: ['handover', handoverId] })
  }
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
  }
}

export function invalidateAfterNotificationChange(queryClient) {
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
}

export function invalidateAfterItemChange(queryClient, itemId) {
  queryClient.invalidateQueries({ queryKey: ['my-lost-items'] })
  queryClient.invalidateQueries({ queryKey: ['my-found-items'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  if (itemId) {
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }
}

export function invalidateAfterProfileUpdate(queryClient) {
  queryClient.invalidateQueries({ queryKey: ['me'] })
  queryClient.invalidateQueries({ queryKey: ['profile'] })
}

export function invalidateAfterReturn(queryClient, { matchId, returnId, lostItemId, foundItemId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['my-returns'] })
  queryClient.invalidateQueries({ queryKey: ['public-returned'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-lost-items'] })
  queryClient.invalidateQueries({ queryKey: ['my-found-items'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  queryClient.invalidateQueries({ queryKey: ['my-claims'] })
  queryClient.invalidateQueries({ queryKey: ['my-awaiting-confirmation'] })
  queryClient.invalidateQueries({ queryKey: ['me'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  markPushPromptReady()
  if (matchId) {
    queryClient.invalidateQueries({ queryKey: ['return-status', matchId] })
  }
  if (returnId) {
    queryClient.invalidateQueries({ queryKey: ['return-detail', returnId] })
  }
  if (lostItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', lostItemId] })
    queryClient.invalidateQueries({ queryKey: ['return-status-by-item', lostItemId] })
  }
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
    queryClient.invalidateQueries({ queryKey: ['return-status-by-item', foundItemId] })
  }
}
