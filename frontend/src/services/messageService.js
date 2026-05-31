import api from './api'

export async function listConversations() {
  const { data } = await api.get('/messages/conversations')
  return data
}

export async function getUnreadMessageCount() {
  const { data } = await api.get('/messages/unread-count')
  return data.total_unread ?? 0
}

export async function getConversation(conversationId) {
  const { data } = await api.get(`/messages/conversations/${conversationId}`)
  return data
}

export async function listMessages(conversationId, { beforeId, limit = 50 } = {}) {
  const params = { limit }
  if (beforeId) params.before_id = beforeId
  const { data } = await api.get(`/messages/conversations/${conversationId}/messages`, { params })
  return data
}

export async function sendMessage(conversationId, body) {
  const { data } = await api.post(`/messages/conversations/${conversationId}/messages`, { body })
  return data
}

export async function markConversationRead(conversationId) {
  await api.post(`/messages/conversations/${conversationId}/read`)
}
