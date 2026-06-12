/**
 * Global Axios instance with JWT refresh interceptor (Section 5.4).
 *
 * Access token  — stored in memory (module variable), 15-min lifetime.
 * Refresh token — httpOnly cookie managed by the browser, 7-day lifetime.
 *
 * Interceptor behaviour:
 *  1. Every request attaches the in-memory access token as Authorization header.
 *  2. On 401 Unauthorized: calls POST /auth/refresh (browser sends cookie automatically).
 *  3. On success: stores new access token, retries the original request.
 *  4. On refresh failure: clears local auth state and redirects to /login.
 */
import axios from 'axios'

export function getApiBaseUrl() {
  const configured = (import.meta.env.VITE_API_URL || '').trim()
  if (!configured) return '/api/v1'
  const root = configured.replace(/\/+$/, '')
  return root.endsWith('/api/v1') ? root : `${root}/api/v1`
}

const BASE_URL = getApiBaseUrl()

// ── In-memory access token (never stored in localStorage / sessionStorage) ──
let _accessToken = null

export const setAccessToken = (token) => { _accessToken = token }
export const getAccessToken  = ()      => _accessToken
export const clearAccessToken = ()     => { _accessToken = null }

// ── Axios instance ────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,   // allows browser to send the httpOnly refresh-token cookie
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// ── Request interceptor — attach access token ──────────────────────────────
api.interceptors.request.use(
  (config) => {
    if (_accessToken) {
      config.headers['Authorization'] = `Bearer ${_accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Shared refresh (AuthContext + interceptor must use the same mutex) ───────
let _isRefreshing = false
let _failedQueue  = []
let _authBootstrap = false

/** True while AuthContext silent-refresh runs on hard reload. */
export function setAuthBootstrapActive(active) {
  _authBootstrap = Boolean(active)
}

const _processQueue = (error, token = null) => {
  _failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  _failedQueue = []
}

/**
 * Rotate the refresh cookie and return a new access token.
 * Single-flight — concurrent callers share one in-flight refresh.
 */
export async function refreshAccessToken({ emitExpired = true } = {}) {
  if (_isRefreshing) {
    return new Promise((resolve, reject) => {
      _failedQueue.push({ resolve, reject })
    })
  }

  _isRefreshing = true
  try {
    const { data } = await axios.post(
      `${BASE_URL}/auth/refresh`,
      {},
      { withCredentials: true },
    )
    const newToken = data.access_token
    setAccessToken(newToken)
    _processQueue(null, newToken)
    return newToken
  } catch (refreshError) {
    _processQueue(refreshError, null)
    clearAccessToken()
    if (emitExpired && !_authBootstrap) {
      window.dispatchEvent(new CustomEvent('faind:auth:expired'))
    }
    throw refreshError
  } finally {
    _isRefreshing = false
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Only attempt refresh on 401, and not for the refresh endpoint itself
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== '/auth/refresh'
    ) {
      originalRequest._retry = true

      try {
        const newToken = await refreshAccessToken({ emitExpired: !_authBootstrap })
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api
