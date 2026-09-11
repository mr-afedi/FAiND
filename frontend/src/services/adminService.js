/**
 * Admin dashboard API (Feature R) — requires X-Admin-Secret-Path header.
 */
import api from './api'

const STORAGE_KEY = 'faind_admin_secret_path'

export function getConfiguredAdminSecret() {
  return import.meta.env.VITE_ADMIN_SECRET_PATH || ''
}

export function rememberAdminSecret(path) {
  if (path) sessionStorage.setItem(STORAGE_KEY, path)
}

export function getAdminSecret() {
  return sessionStorage.getItem(STORAGE_KEY) || getConfiguredAdminSecret()
}

export function isValidAdminSecret(path) {
  const configured = getConfiguredAdminSecret()
  if (!configured || !path) return false
  return path === configured
}

function adminConfig() {
  return { headers: { 'X-Admin-Secret-Path': getAdminSecret() } }
}

export async function adminGate() {
  const { data } = await api.get('/admin/gate', adminConfig())
  return data
}

export async function getAnalytics() {
  const { data } = await api.get('/admin/analytics', adminConfig())
  return data
}

export async function adminSearch(q) {
  const { data } = await api.get('/admin/search', { ...adminConfig(), params: { q } })
  return data
}

export async function listUsers(params = {}) {
  const { data } = await api.get('/admin/users', { ...adminConfig(), params })
  return data
}

export async function suspendUser(userId, reason) {
  const { data } = await api.post(
    `/admin/users/${userId}/suspend`,
    { reason },
    adminConfig(),
  )
  return data
}

export async function unsuspendUser(userId) {
  const { data } = await api.post(`/admin/users/${userId}/unsuspend`, {}, adminConfig())
  return data
}

export async function trustAdjustUser(userId, delta, reason) {
  const { data } = await api.post(
    `/admin/users/${userId}/trust-adjust`,
    { delta, reason },
    adminConfig(),
  )
  return data
}

export async function lockDisputeItem(disputeId, reason, disputeType) {
  const { data } = await api.post(
    `/admin/disputes/${disputeId}/lock-item`,
    { reason },
    { ...adminConfig(), params: disputeType ? { dispute_type: disputeType } : undefined },
  )
  return data
}

export async function escalateDispute(disputeId, note, disputeType) {
  const { data } = await api.post(
    `/admin/disputes/${disputeId}/escalate`,
    { note },
    { ...adminConfig(), params: disputeType ? { dispute_type: disputeType } : undefined },
  )
  return data
}

export async function listClaims(params = {}) {
  const { data } = await api.get('/admin/claims', { ...adminConfig(), params })
  return data
}

export async function approveClaim(matchId) {
  const { data } = await api.post(`/admin/claims/${matchId}/approve`, {}, adminConfig())
  return data
}

export async function rejectClaim(matchId, note) {
  const { data } = await api.post(`/admin/claims/${matchId}/reject`, { note }, adminConfig())
  return data
}

export async function requestClaimInfo(matchId, note) {
  const { data } = await api.post(
    `/admin/claims/${matchId}/request-info`,
    { note },
    adminConfig(),
  )
  return data
}

export async function getClaimDetail(matchId) {
  const { data } = await api.get(`/admin/claims/${matchId}`, adminConfig())
  return data.detail
}

export async function listDisputes() {
  const { data } = await api.get('/admin/disputes', adminConfig())
  return data
}

export async function resolveDispute(returnId, outcome, note) {
  const { data } = await api.post(
    `/admin/disputes/${returnId}/resolve`,
    { outcome, note },
    adminConfig(),
  )
  return data
}

export async function resolveVerificationDispute(matchId, winnerMatchId, note) {
  const { data } = await api.post(
    `/admin/disputes/verification/${matchId}/resolve`,
    { winner_match_id: winnerMatchId, note },
    adminConfig(),
  )
  return data
}

export async function getDisputeDetail(disputeId, disputeType) {
  const { data } = await api.get(`/admin/disputes/${disputeId}`, {
    ...adminConfig(),
    params: disputeType ? { dispute_type: disputeType } : undefined,
  })
  return data.detail
}

export async function listReports(status = 'pending') {
  const { data } = await api.get('/admin/reports', {
    ...adminConfig(),
    params: { status },
  })
  return data
}

export async function dismissPostReport(reportId) {
  const { data } = await api.post(`/admin/reports/posts/${reportId}/dismiss`, {}, adminConfig())
  return data
}

export async function removeReportedPost(reportId) {
  const { data } = await api.post(`/admin/reports/posts/${reportId}/remove-post`, {}, adminConfig())
  return data
}

export async function dismissUserReport(reportId) {
  const { data } = await api.post(`/admin/reports/users/${reportId}/dismiss`, {}, adminConfig())
  return data
}

export async function warnUserReport(reportId) {
  const { data } = await api.post(`/admin/reports/users/${reportId}/warn`, {}, adminConfig())
  return data
}

export async function suspendUserReport(reportId) {
  const { data } = await api.post(`/admin/reports/users/${reportId}/suspend`, {}, adminConfig())
  return data
}

export async function suppressReporter(userId) {
  const { data } = await api.post(`/admin/reports/reporters/${userId}/suppress`, {}, adminConfig())
  return data
}

export async function getReportDetail(reportId, reportType) {
  const { data } = await api.get(`/admin/reports/${reportId}`, {
    ...adminConfig(),
    params: { report_type: reportType },
  })
  return data.detail
}

export async function listFraudAlerts() {
  const { data } = await api.get('/admin/fraud/alerts', adminConfig())
  return data
}

export async function confirmFraud(userId) {
  const { data } = await api.post(`/admin/fraud/users/${userId}/confirm`, {}, adminConfig())
  return data
}

export async function clearFraudFlag(userId) {
  const { data } = await api.post(`/admin/fraud/users/${userId}/clear`, {}, adminConfig())
  return data
}

export async function allowVerification(userId) {
  const { data } = await api.post(
    `/admin/fraud/users/${userId}/allow-verification`,
    {},
    adminConfig(),
  )
  return data
}

export async function getFraudDetail(userId) {
  const { data } = await api.get(`/admin/fraud/${userId}/detail`, adminConfig())
  return data.detail
}

export async function listReturnedItems(params = {}) {
  const { data } = await api.get('/admin/returns', { ...adminConfig(), params })
  return data
}

export async function getReturnedDetail(returnId) {
  const { data } = await api.get(`/admin/returns/${returnId}`, adminConfig())
  return data.detail
}

export async function openReturnDispute(returnId, reason) {
  const { data } = await api.post(
    `/admin/returns/${returnId}/open-dispute`,
    { reason },
    adminConfig(),
  )
  return data
}

export async function listUniversities() {
  const { data } = await api.get('/universities/')
  return data
}

export async function listPostsModeration(params = {}) {
  const { data } = await api.get('/admin/posts', { ...adminConfig(), params })
  return data
}

export async function forceClosePost(itemId, reason) {
  const { data } = await api.post(
    `/admin/posts/${itemId}/force-close`,
    { reason },
    adminConfig(),
  )
  return data
}

export async function removePost(itemId, reason) {
  const { data } = await api.post(
    `/admin/posts/${itemId}/remove`,
    { reason },
    adminConfig(),
  )
  return data
}

export async function getPostDetail(itemId) {
  const { data } = await api.get(`/admin/posts/${itemId}`, adminConfig())
  return data.detail
}

export async function getUserDetail(userId) {
  const { data } = await api.get(`/admin/users/${userId}/detail`, adminConfig())
  return data.detail
}

export async function listAdminLogs(params = {}) {
  const { data } = await api.get('/admin/logs', { ...adminConfig(), params })
  return data
}

export async function promoteAdmin(userId) {
  const { data } = await api.post('/admin/admins/promote', { user_id: userId }, adminConfig())
  return data
}

export async function demoteAdmin(userId) {
  const { data } = await api.post(`/admin/admins/${userId}/demote`, {}, adminConfig())
  return data
}

export function isAdminRole(role) {
  return role === 'root_admin' || role === 'assistant_root_admin'
}
