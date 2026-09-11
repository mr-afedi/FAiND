import api from './api'

export async function initializeTip(returnId, amountGhs) {
  const { data } = await api.post(`/tips/returns/${returnId}/initialize`, {
    amount_ghs: amountGhs,
  })
  return data
}

export async function verifyTip(reference) {
  const { data } = await api.get(`/tips/verify/${encodeURIComponent(reference)}`)
  return data
}

export async function listSentTips() {
  const { data } = await api.get('/tips/me/sent')
  return data
}

export async function listReceivedTips() {
  const { data } = await api.get('/tips/me/received')
  return data
}
