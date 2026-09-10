import api from './api'

export const userService = {
  async getMe() {
    const res = await api.get('/users/me')
    return res.data
  },

  async updateProfile(data) {
    const res = await api.patch('/users/me', data)
    return res.data
  },

  async changePassword(currentPassword, newPassword, confirmPassword) {
    const res = await api.patch('/users/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    })
    return res.data
  },

  async updateSettings(data) {
    const res = await api.patch('/users/me/settings', data)
    return res.data
  },

  async deleteAccount(password) {
    const res = await api.delete('/users/me', {
      data: { password, confirmation: 'DELETE' },
    })
    return res.data
  },

  async getPublicProfile(username) {
    const res = await api.get(`/users/${username}`)
    return res.data
  },
}
