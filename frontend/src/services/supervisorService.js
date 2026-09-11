/**
 * Supervisor API — separate JWT from user/authority auth (Section 15.2).
 */
import axios from 'axios'
import { getApiBaseUrl } from './api'

const SUPERVISOR_SESSION_FLAG = 'faind_supervisor_session'
const SUPERVISOR_TOKEN_KEY = 'faind_supervisor_access_token'

let _supervisorAccessToken = sessionStorage.getItem(SUPERVISOR_TOKEN_KEY) || null

export const setSupervisorAccessToken = (token) => {
  _supervisorAccessToken = token
  if (token) sessionStorage.setItem(SUPERVISOR_TOKEN_KEY, token)
  else sessionStorage.removeItem(SUPERVISOR_TOKEN_KEY)
}
export const getSupervisorAccessToken = () => _supervisorAccessToken
export const clearSupervisorAccessToken = () => {
  _supervisorAccessToken = null
  sessionStorage.removeItem(SUPERVISOR_TOKEN_KEY)
}

export function setSupervisorSessionActive(active) {
  if (active) sessionStorage.setItem(SUPERVISOR_SESSION_FLAG, '1')
  else sessionStorage.removeItem(SUPERVISOR_SESSION_FLAG)
}

const supervisorApi = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

supervisorApi.interceptors.request.use((config) => {
  if (_supervisorAccessToken) {
    config.headers.Authorization = `Bearer ${_supervisorAccessToken}`
  }
  return config
})

export async function supervisorLogin(email, password) {
  const { data } = await supervisorApi.post('/supervisor/login', { email, password })
  return data
}

export async function getSupervisorMe() {
  const { data } = await supervisorApi.get('/supervisor/me')
  return data
}

export async function getSupervisorItems(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/items', {
    params: dropPointId ? { drop_point_id: dropPointId } : undefined,
  })
  return data
}

export async function getSupervisorClaimsList(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/claims', {
    params: dropPointId ? { drop_point_id: dropPointId } : undefined,
  })
  return data
}

export async function getSupervisorClaimsForItem(foundItemId) {
  const { data } = await supervisorApi.get(`/supervisor/claims/${foundItemId}`)
  return data
}

export async function listSupervisorAuthorities() {
  const { data } = await supervisorApi.get('/supervisor/authorities')
  return data
}

export async function createSupervisorAuthority(payload) {
  const { data } = await supervisorApi.post('/supervisor/authorities', payload)
  return data
}

export async function deactivateSupervisorAuthority(authorityId) {
  const { data } = await supervisorApi.patch(`/supervisor/authorities/${authorityId}/deactivate`)
  return data
}

export async function activateSupervisorAuthority(authorityId) {
  const { data } = await supervisorApi.patch(`/supervisor/authorities/${authorityId}/activate`)
  return data
}

export async function resetSupervisorAuthorityPassword(authorityId, password) {
  const { data } = await supervisorApi.post(`/supervisor/authorities/${authorityId}/reset-password`, {
    password,
  })
  return data
}

export async function supervisorLookupRedemptionCode(code) {
  const { data } = await supervisorApi.post('/supervisor/redemption/lookup', { code })
  return data
}

export async function getSupervisorOverview(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/overview', {
    params: dropPointId ? { drop_point_id: dropPointId } : undefined,
  })
  return data
}

export async function getSupervisorIncoming(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/incoming', {
    params: dropPointId ? { drop_point_id: dropPointId } : undefined,
  })
  return data
}

export async function getSupervisorAtDroppoint(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/at-droppoint', {
    params: dropPointId ? { drop_point_id: dropPointId } : undefined,
  })
  return data
}

export async function getSupervisorHandoverQueue(dropPointId) {
  const { data } = await supervisorApi.get('/supervisor/handover', {
    params: {
      completed_only: true,
      ...(dropPointId ? { drop_point_id: dropPointId } : {}),
    },
  })
  return data
}

export async function getSupervisorHandover(handoverId) {
  const { data } = await supervisorApi.get(`/supervisor/handover/${handoverId}`)
  return data
}

export async function callSupervisorClaimToCollect(claimId) {
  const { data } = await supervisorApi.post(`/supervisor/claims/${claimId}/call-to-collect`)
  return data
}

export async function verifySupervisorClaim(claimId) {
  const { data } = await supervisorApi.post(`/supervisor/claims/${claimId}/verify`)
  return data
}

export async function rejectSupervisorClaim(claimId) {
  const { data } = await supervisorApi.post(`/supervisor/claims/${claimId}/reject`)
  return data
}

export async function replyToSupervisorInquiry(inquiryId, replyType) {
  const { data } = await supervisorApi.post(`/supervisor/inquiries/${inquiryId}/reply`, {
    reply_type: replyType,
  })
  return data
}

export async function escalateSupervisorDispute(foundItemId, note) {
  const { data } = await supervisorApi.post(`/supervisor/disputes/${foundItemId}/escalate`, { note })
  return data
}

export async function getSupervisorAlerts({ skip = 0, limit = 50 } = {}) {
  const { data } = await supervisorApi.get('/supervisor/alerts', { params: { skip, limit } })
  return data
}

export async function markSupervisorAlertRead(alertId) {
  const { data } = await supervisorApi.patch(`/supervisor/alerts/${alertId}/read`)
  return data
}

export async function markAllSupervisorAlertsRead() {
  const { data } = await supervisorApi.post('/supervisor/alerts/read-all')
  return data
}

export async function deleteSupervisorAlert(alertId) {
  const { data } = await supervisorApi.delete(`/supervisor/alerts/${alertId}`)
  return data
}

export async function clearDeletableSupervisorAlerts() {
  const { data } = await supervisorApi.post('/supervisor/alerts/clear-deletable')
  return data
}

export { supervisorApi }
