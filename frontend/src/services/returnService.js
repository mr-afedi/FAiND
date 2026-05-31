import api from './api'

export async function getReturnStatus(matchId) {
  const res = await api.get(`/returns/match/${matchId}/status`)
  return res.data
}

export async function getReturnStatusByItem(itemId) {
  const res = await api.get(`/returns/by-item/${itemId}/status`)
  return res.data
}

export async function finderConfirmHandover(matchId) {
  const res = await api.post(`/returns/match/${matchId}/finder-confirm`)
  return res.data
}

export async function ownerConfirmReceipt(matchId) {
  const res = await api.post(`/returns/match/${matchId}/owner-confirm`)
  return res.data
}

export async function generateReturnQr(matchId) {
  const res = await api.post(`/returns/match/${matchId}/qr/generate`)
  return res.data
}

export async function redeemReturnQr(token) {
  const res = await api.post('/returns/qr/redeem', { token })
  return res.data
}

export async function listMyReturns() {
  const res = await api.get('/returns/me')
  return res.data
}

export async function getReturnDetail(returnId) {
  const res = await api.get(`/returns/${returnId}`)
  return res.data
}

export async function skipAppreciation(returnId) {
  const res = await api.post(`/returns/${returnId}/skip-appreciation`)
  return res.data
}

export async function disputeReturn(returnId, reason) {
  const res = await api.post(`/returns/${returnId}/dispute`, { reason })
  return res.data
}
