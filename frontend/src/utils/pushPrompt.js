/**
 * Contextual push-permission prompt state (Section 11.3 / 29.2).
 * Prompt is shown only after a notification-worthy event — never on login.
 */

export const PUSH_PROMPT_READY_KEY = 'faind:push_prompt_ready'
export const PUSH_PROMPT_DISMISSED_KEY = 'faind:push_prompt_dismissed'
export const PUSH_PROMPT_READY_EVENT = 'faind:push-prompt-ready'

/** In-app notification types that should trigger the push opt-in banner. */
export const NOTIFICATION_WORTHY_TYPES = new Set([
  'match_found',
  'potential_match_expired',
  'verification_passed',
  'verification_failed',
  'verification_review',
  'claim_received',
  'item_returned',
  'post_expiring',
])

export function isPushPromptReady() {
  return localStorage.getItem(PUSH_PROMPT_READY_KEY) === 'true'
}

export function markPushPromptReady() {
  if (localStorage.getItem(PUSH_PROMPT_READY_KEY) === 'true') return
  localStorage.setItem(PUSH_PROMPT_READY_KEY, 'true')
  window.dispatchEvent(new Event(PUSH_PROMPT_READY_EVENT))
}

export function dismissPushPrompt() {
  localStorage.setItem(PUSH_PROMPT_DISMISSED_KEY, 'true')
}

export function isPushPromptDismissed() {
  return localStorage.getItem(PUSH_PROMPT_DISMISSED_KEY) === 'true'
}
