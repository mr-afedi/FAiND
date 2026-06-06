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

export async function listClaims() {
  const { data } = await api.get('/admin/claims', adminConfig())
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

export async function listFraudAlerts() {
  const { data } = await api.get('/admin/fraud/alerts', adminConfig())
  return data
}

export async function confirmFraud(userId) {
  const { data } = await api.post(`/admin/fraud/users/${userId}/confirm`, {}, adminConfig())
  return data
}

export async function listPostsModeration() {
  const { data } = await api.get('/admin/posts', adminConfig())
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

export async function listAdminLogs() {
  const { data } = await api.get('/admin/logs', adminConfig())
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
