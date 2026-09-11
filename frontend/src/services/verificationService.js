import api from './api'

export async function getPathAForm(matchId) {
  const res = await api.get(`/verification/path-a/${matchId}/form`)
  return res.data
}

export async function getPathAStatus(matchId) {
  const res = await api.get(`/verification/path-a/${matchId}/status`)
  return res.data
}

export async function submitPathA(matchId, answers) {
  const res = await api.post(`/verification/path-a/${matchId}`, { answers }, {
    timeout: 60_000,
  })
  return res.data
}

export function isAmbiguousVerificationError(err) {
  if (!err) return false
  if (err.code === 'ECONNABORTED') return true
  return !err.response
}
