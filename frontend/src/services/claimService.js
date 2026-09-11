/**
 * Claims API — Path A/C (Section 8) and structured messaging (Section 13).
 */
import api from './api'

export async function submitClaimPathA(foundItemId, payload) {
  const { data } = await api.post(`/claims/path-a/${foundItemId}`, payload)
  return data
}

export async function submitClaimPathC(foundItemId, payload) {
  const { data } = await api.post(`/claims/path-c/${foundItemId}`, payload)
  return data
}

export async function getClaimStatus(claimId) {
  const { data } = await api.get(`/claims/${claimId}/status`)
  return data
}

export async function getMyClaims() {
  const { data } = await api.get('/claims/me')
  return data
}

export async function getAwaitingConfirmation() {
  const { data } = await api.get('/claims/me/awaiting-confirmation')
  return data
}

export async function sendClaimInquiry(claimId, messageType) {
  const { data } = await api.post(`/claims/${claimId}/inquiry`, {
    message_type: messageType,
  })
  return data
}

export const INQUIRY_OPTIONS = [
  { value: 'still_available', label: 'Is this item still available for collection?' },
  { value: 'on_my_way', label: 'I am on my way to collect' },
  { value: 'collect_tomorrow', label: 'I cannot collect today, can I come tomorrow?' },
]

export const REPLY_OPTIONS = [
  { value: 'yes_here', label: 'Yes, it is here' },
  { value: 'come_during_hours', label: 'Please come during operating hours' },
  { value: 'already_collected', label: 'This item has already been collected by someone else' },
  { value: 'no_response_needed', label: 'No response needed' },
]

export function replyLabel(option, operatingHours) {
  if (option.value === 'come_during_hours' && operatingHours) {
    return `Please come between ${operatingHours}`
  }
  return option.label
}
