import api from './api'

export const authService = {
  async register(data) {
    const res = await api.post('/auth/register', data)
    return res.data
  },

  async verifyEmail(email, code) {
    const res = await api.post('/auth/verify-email', { email, code })
    return res.data   // { access_token, user }
  },

  async resendVerification(email) {
    const res = await api.post('/auth/resend-verification', { email })
    return res.data
  },

  async login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    return res.data   // { access_token, user } or { requires_totp, session_token }
  },

  async totpVerify(sessionToken, totpCode) {
    const res = await api.post('/auth/totp-verify', {
      session_token: sessionToken,
      totp_code: totpCode,
    })
    return res.data
  },

  async logout() {
    const res = await api.post('/auth/logout')
    return res.data
  },

  async forgotPassword(email) {
    const res = await api.post('/auth/forgot-password', { email })
    return res.data
  },

  async resetPassword(email, code, newPassword, confirmPassword) {
    const res = await api.post('/auth/reset-password', {
      email,
      code,
      new_password: newPassword,
      confirm_password: confirmPassword,
    })
    return res.data
  },

  async getMe() {
    const res = await api.get('/auth/me')
    return res.data
  },
}
