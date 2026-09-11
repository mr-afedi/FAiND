import api from './api'

export async function reportPost(itemId, { reason, detail_text }) {
  const { data } = await api.post(`/reports/items/${itemId}`, {
    reason,
    detail_text: detail_text || null,
  })
  return data
}

export async function reportUser(userId, { reason, detail_text, conversation_id }) {
  const { data } = await api.post(`/reports/users/${userId}`, {
    reason,
    detail_text: detail_text || null,
    conversation_id: conversation_id || null,
  })
  return data
}
