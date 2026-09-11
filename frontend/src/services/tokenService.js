import api from './api'

export async function getEscrowStatus(escrowToken) {
  const { data } = await api.get('/tokens/escrow/status', {
    params: { escrow_token: escrowToken },
  })
  return data.escrow
}

export async function discardEscrow(escrowToken) {
  await api.post('/tokens/escrow/discard', { escrow_token: escrowToken })
}

export async function claimEscrowLogin({ escrowToken, email, password }) {
  const { data } = await api.post('/tokens/escrow/claim/login', {
    escrow_token: escrowToken,
    email,
    password,
  })
  return data
}

export async function claimEscrowRegister({ escrowToken, ...registerFields }) {
  const { data } = await api.post('/tokens/escrow/claim/register', {
    escrow_token: escrowToken,
    ...registerFields,
  })
  return data
}

export async function claimEscrowMe(escrowToken) {
  const { data } = await api.post('/tokens/escrow/claim/me', {
    escrow_token: escrowToken,
  })
  return data
}

export async function getMyTokens() {
  const { data } = await api.get('/users/me/tokens')
  return data
}

export async function redeemTokens(tokenAmount) {
  const { data } = await api.post('/users/me/tokens/redeem', {
    token_amount: tokenAmount,
  })
  return data
}
