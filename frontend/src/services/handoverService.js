/**
 * Owner handover digital sign-off — Section 11.
 */
import api from './api'

export async function getHandover(handoverId) {
  const { data } = await api.get(`/handover/${handoverId}`)
  return data
}

export async function confirmHandover(handoverId) {
  const { data } = await api.post(`/handover/${handoverId}/confirm`)
  return data
}
