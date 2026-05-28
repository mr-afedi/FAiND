import api from './api'

export async function getPathBForm(lostItemId) {
  const res = await api.get(`/verification/path-b/lost-items/${lostItemId}/form`)
  return res.data
}

export async function submitPathB(lostItemId, payload) {
  const res = await api.post(`/verification/path-b/lost-items/${lostItemId}`, payload)
  return res.data
}
