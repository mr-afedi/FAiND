import api from './api'

export async function getPathCForm(foundItemId) {
  const res = await api.get(`/verification/path-c/found-items/${foundItemId}/form`)
  return res.data
}

export async function submitPathC(foundItemId, payload) {
  const res = await api.post(`/verification/path-c/found-items/${foundItemId}`, payload)
  return res.data
}
