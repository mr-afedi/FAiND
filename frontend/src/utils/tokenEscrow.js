const ESCROW_KEY = 'faind_token_escrow'

export function getEscrowToken() {
  try {
    return localStorage.getItem(ESCROW_KEY) || ''
  } catch {
    return ''
  }
}

export function saveEscrowToken(token) {
  if (!token) return
  try {
    localStorage.setItem(ESCROW_KEY, token)
  } catch {
    // ignore quota / private mode
  }
}

export function clearEscrowToken() {
  try {
    localStorage.removeItem(ESCROW_KEY)
  } catch {
    // ignore
  }
}
