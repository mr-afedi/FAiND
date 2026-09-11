/** Chat helpers — bubble side is always derived from auth user vs sender_id. */

export const CHAT_EVENT = 'faind:chat'

export function isMessageMine(message, userId) {
  if (!message || userId == null) return false
  return String(message.sender_id) === String(userId)
}

/** Normalize API/WS payload so is_mine matches the viewing user (not the sender). */
export function normalizeMessage(message, userId) {
  const mine = isMessageMine(message, userId)
  return {
    ...message,
    is_mine: mine,
    is_seen: mine ? Boolean(message.read_at) : false,
  }
}

export function getActiveConversationId() {
  const m = window.location.pathname.match(/^\/messages\/([^/]+)/)
  return m?.[1] ?? null
}
