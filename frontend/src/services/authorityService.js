/**
 * Authority API client — separate JWT from regular user auth (Section 16).
 */
import axios from 'axios'
import { getApiBaseUrl } from './api'

const AUTHORITY_SESSION_FLAG = 'faind_authority_session'
const AUTHORITY_TOKEN_KEY = 'faind_authority_access_token'
const AUTHORITY_OTP_SESSION_KEY = 'faind_authority_otp_session'
const AUTHORITY_SESSION_EXPIRED_FLAG = 'faind_authority_session_expired'

let _authorityAccessToken = sessionStorage.getItem(AUTHORITY_TOKEN_KEY) || null

export const setAuthorityAccessToken = (token) => {
  _authorityAccessToken = token
  if (token) sessionStorage.setItem(AUTHORITY_TOKEN_KEY, token)
  else sessionStorage.removeItem(AUTHORITY_TOKEN_KEY)
}
export const getAuthorityAccessToken = () => _authorityAccessToken
export const clearAuthorityAccessToken = () => {
  _authorityAccessToken = null
  sessionStorage.removeItem(AUTHORITY_TOKEN_KEY)
}

export function setAuthoritySessionActive(active) {
  if (active) sessionStorage.setItem(AUTHORITY_SESSION_FLAG, '1')
  else sessionStorage.removeItem(AUTHORITY_SESSION_FLAG)
}

export function hasAuthoritySessionFlag() {
  return sessionStorage.getItem(AUTHORITY_SESSION_FLAG) === '1'
}

export function markAuthoritySessionExpired() {
  sessionStorage.setItem(AUTHORITY_SESSION_EXPIRED_FLAG, '1')
}

export function consumeAuthoritySessionExpired() {
  const expired = sessionStorage.getItem(AUTHORITY_SESSION_EXPIRED_FLAG) === '1'
  if (expired) sessionStorage.removeItem(AUTHORITY_SESSION_EXPIRED_FLAG)
  return expired
}

export function rememberAuthorityOtpSession(sessionToken) {
  if (sessionToken) {
    sessionStorage.setItem(AUTHORITY_OTP_SESSION_KEY, sessionToken)
  }
}

export function getAuthorityOtpSession() {
  return sessionStorage.getItem(AUTHORITY_OTP_SESSION_KEY) || ''
}

export function clearAuthorityOtpSession() {
  sessionStorage.removeItem(AUTHORITY_OTP_SESSION_KEY)
}

const authorityApi = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

authorityApi.interceptors.request.use((config) => {
  if (_authorityAccessToken) {
    config.headers.Authorization = `Bearer ${_authorityAccessToken}`
  }
  return config
})

authorityApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401
      && (_authorityAccessToken || hasAuthoritySessionFlag())
      && !error.config?.url?.includes('/authority/login')
      && !error.config?.url?.includes('/authority/verify-otp')
    ) {
      markAuthoritySessionExpired()
      clearAuthorityAccessToken()
      setAuthoritySessionActive(false)
      if (!window.location.pathname.startsWith('/login')
        && !window.location.pathname.startsWith('/authority/otp')) {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export async function authorityLogin(email, password) {
  const { data } = await authorityApi.post('/authority/login', { email, password })
  return data
}

export async function authorityVerifyOtp(sessionToken, code) {
  const token = (sessionToken || getAuthorityOtpSession()).trim()
  const normalizedCode = String(code || '').trim()
  if (!token) {
    throw new Error('Your sign-in session expired. Please log in again.')
  }
  if (!/^\d{6}$/.test(normalizedCode)) {
    throw new Error('Enter the full 6-digit code from your email (include any leading zeros).')
  }
  const { data } = await authorityApi.post('/authority/verify-otp', {
    session_token: token,
    code: normalizedCode,
  })
  clearAuthorityOtpSession()
  return data
}

export async function getAuthorityMe() {
  const { data } = await authorityApi.get('/authority/me')
  return data
}

export async function getAuthorityItem(itemId) {
  const { data } = await authorityApi.get(`/authority/items/${itemId}`)
  return data
}

export async function getAuthorityIncoming() {
  const { data } = await authorityApi.get('/authority/incoming')
  return data
}

export async function getAuthorityAtDroppoint() {
  const { data } = await authorityApi.get('/authority/at-droppoint')
  return data
}

export async function confirmAuthorityDropoff(itemId) {
  const { data } = await authorityApi.post(`/authority/confirm-dropoff/${itemId}`)
  return data
}

export async function scanAuthorityQr(token) {
  const { data } = await authorityApi.post('/authority/scan-qr', { token })
  return data
}

export async function getAuthorityDropPointSettings() {
  const { data } = await authorityApi.get('/authority/drop-point/settings')
  return data
}

export async function updateAuthorityDropPointSettings(payload) {
  const { data } = await authorityApi.patch('/authority/drop-point/settings', payload)
  return data
}

export async function getAuthorityClaimsList() {
  const { data } = await authorityApi.get('/authority/claims')
  return data
}

export async function getAuthorityClaimsForItem(foundItemId) {
  const { data } = await authorityApi.get(`/authority/claims/${foundItemId}`)
  return data
}

export async function callAuthorityClaimToCollect(claimId) {
  const { data } = await authorityApi.post(`/authority/claims/${claimId}/call-to-collect`)
  return data
}

export async function verifyAuthorityClaim(claimId) {
  const { data } = await authorityApi.post(`/authority/claims/${claimId}/verify`)
  return data
}

export async function rejectAuthorityClaim(claimId) {
  const { data } = await authorityApi.post(`/authority/claims/${claimId}/reject`)
  return data
}

export async function replyToClaimInquiry(inquiryId, replyType) {
  const { data } = await authorityApi.post(`/authority/inquiries/${inquiryId}/reply`, {
    reply_type: replyType,
  })
  return data
}

export async function getAuthorityHandoverQueue() {
  const { data } = await authorityApi.get('/authority/handover')
  return data
}

export async function getAuthorityHandover(handoverId) {
  const { data } = await authorityApi.get(`/authority/handover/${handoverId}`)
  return data
}

export async function startAuthorityHandover(claimId, payload) {
  const { data } = await authorityApi.post(`/authority/handover/${claimId}/start`, payload)
  return data
}

export async function overrideAuthorityHandover(handoverId, note) {
  const { data } = await authorityApi.post(`/authority/handover/${handoverId}/override`, { note })
  return data
}

export async function getAuthorityAlerts({ skip = 0, limit = 50 } = {}) {
  const { data } = await authorityApi.get('/authority/alerts', { params: { skip, limit } })
  return data
}

export async function markAuthorityAlertRead(alertId) {
  const { data } = await authorityApi.patch(`/authority/alerts/${alertId}/read`)
  return data
}

export async function markAllAuthorityAlertsRead() {
  const { data } = await authorityApi.post('/authority/alerts/read-all')
  return data
}

export async function deleteAuthorityAlert(alertId) {
  const { data } = await authorityApi.delete(`/authority/alerts/${alertId}`)
  return data
}

export async function clearDeletableAuthorityAlerts() {
  const { data } = await authorityApi.post('/authority/alerts/clear-deletable')
  return data
}

export default authorityApi
