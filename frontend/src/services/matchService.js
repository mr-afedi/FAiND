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
