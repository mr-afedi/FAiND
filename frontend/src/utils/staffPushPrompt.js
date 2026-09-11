export function staffPushPromptReadyKey(role) {
  return `faind:${role}:push_prompt_ready`
}

export function staffPushPromptDismissedKey(role) {
  return `faind:${role}:push_prompt_dismissed`
}

export function STAFF_PUSH_PROMPT_READY_EVENT(role) {
  return `faind:${role}:push-prompt-ready`
}

export function isStaffPushPromptReady(role) {
  return localStorage.getItem(staffPushPromptReadyKey(role)) === 'true'
}

export function markStaffPushPromptReady(role) {
  const key = staffPushPromptReadyKey(role)
  if (localStorage.getItem(key) === 'true') return
  localStorage.setItem(key, 'true')
  window.dispatchEvent(new Event(STAFF_PUSH_PROMPT_READY_EVENT(role)))
}

export function dismissStaffPushPrompt(role) {
  localStorage.setItem(staffPushPromptDismissedKey(role), 'true')
}

export function isStaffPushPromptDismissed(role) {
  return localStorage.getItem(staffPushPromptDismissedKey(role)) === 'true'
}
