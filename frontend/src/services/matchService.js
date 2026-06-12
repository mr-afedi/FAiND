import api from './api'

export async function getMyMatches() {
  const res = await api.get('/matches/me')
  return res.data
}

export async function getMyNotifications({ skip = 0, limit = 20 } = {}) {
  const res = await api.get('/notifications/me', { params: { skip, limit } })
  return res.data
}

export async function previewMatchScore(lostItemId, foundItemId) {
  const res = await api.post('/matches/preview', {
    lost_item_id: lostItemId,
    found_item_id: foundItemId,
  })
  return res.data
}

export async function markNotificationRead(notificationId) {
  const res = await api.patch(`/notifications/${notificationId}/read`)
  return res.data
}

export async function markAllNotificationsRead() {
  const res = await api.post('/notifications/me/read-all')
  return res.data
}

export async function deleteNotification(notificationId) {
  const res = await api.delete(`/notifications/${notificationId}`)
  return res.data
}

export async function clearDeletableNotifications() {
  const res = await api.post('/notifications/me/clear-deletable')
  return res.data
}

export async function getUnreadNotificationCount() {
  const res = await api.get('/notifications/me', { params: { limit: 1 } })
  return res.data.unread_count ?? 0
}
