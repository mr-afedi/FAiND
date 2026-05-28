/**
 * Shared React Query cache invalidation — call after mutations so UI refreshes
 * without a manual page reload.
 */

export function invalidateAfterItemCreate(queryClient, { type = 'lost' } = {}) {
  queryClient.invalidateQueries({ queryKey: [type === 'lost' ? 'my-lost-items' : 'my-found-items'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
}

export function invalidateAfterItemChange(queryClient, itemId) {
  queryClient.invalidateQueries({ queryKey: ['my-lost-items'] })
  queryClient.invalidateQueries({ queryKey: ['my-found-items'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  if (itemId) {
    queryClient.invalidateQueries({ queryKey: ['item', itemId] })
  }
}

export function invalidateAfterPathC(queryClient, { foundItemId, matchId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['path-c-form', foundItemId] })
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
  }
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  if (matchId) {
    queryClient.invalidateQueries({ queryKey: ['path-a-form', matchId] })
  }
}

export function invalidateAfterPathB(queryClient, { lostItemId, matchId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  queryClient.invalidateQueries({ queryKey: ['homepage'] })
  queryClient.invalidateQueries({ queryKey: ['browse'] })
  queryClient.invalidateQueries({ queryKey: ['path-b-form', lostItemId] })
  if (lostItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', lostItemId] })
  }
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  if (matchId) {
    queryClient.invalidateQueries({ queryKey: ['path-a-form', matchId] })
  }
}

export function invalidateAfterVerification(queryClient, { lostItemId, foundItemId, matchId } = {}) {
  queryClient.invalidateQueries({ queryKey: ['my-matches'] })
  queryClient.invalidateQueries({ queryKey: ['my-matches-for-item'] })
  if (matchId) {
    queryClient.invalidateQueries({ queryKey: ['path-a-form', matchId] })
  }
  if (lostItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', lostItemId] })
  }
  if (foundItemId) {
    queryClient.invalidateQueries({ queryKey: ['item', foundItemId] })
  }
  queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
  queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
  queryClient.invalidateQueries({ queryKey: ['my-trust-events'] })
}

export function invalidateAfterProfileUpdate(queryClient) {
  queryClient.invalidateQueries({ queryKey: ['me'] })
  queryClient.invalidateQueries({ queryKey: ['profile'] })
}
