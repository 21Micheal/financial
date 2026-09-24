/**
 * api.ts — Axios client for the Financial System backend.
 *
 * fix #7A: 401 response interceptor attempts one token refresh before logging out.
 * fix #7C: Calls oidcLogout() before clearing Zustand on final session failure.
 */
import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { oidcLogout } from '../lib/oidcClient'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach Bearer token ───────────────────────────────
apiClient.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// ── Response interceptor: silent token refresh on 401 (fix #7A) ───────────
let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

function processQueue(newToken: string) {
  refreshQueue.forEach((resolve) => resolve(newToken))
  refreshQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (
      error.response?.status !== 401 ||
      original._retry ||
      original.url?.includes('/auth/token/refresh/') ||
      original.url?.includes('/auth/login/') ||
      original.url?.includes('/auth/oidc/exchange/')
    ) {
      return Promise.reject(error)
    }

    const { refreshToken, setTokens, logout } = useAuthStore.getState()
    if (!refreshToken) {
      logout()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve) => {
        refreshQueue.push((token) => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(apiClient(original))
        })
      })
    }

    original._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      })
      setTokens(data.access, data.refresh)
      processQueue(data.access)
      original.headers.Authorization = `Bearer ${data.access}`
      return apiClient(original)
    } catch {
      // Refresh failed — end session (fix #7C: also end Keycloak session)
      oidcLogout().catch(() => {})
      logout()
      return Promise.reject(error)
    } finally {
      isRefreshing = false
    }
  }
)

// ── API surface ────────────────────────────────────────────────────────────
export const authAPI = {
  login:        (email: string, password: string) =>
    apiClient.post('/auth/login/', { email, password }),
  verifyOTP:    (userId: string, otp: string) =>
    apiClient.post('/auth/verify-otp/', { user_id: userId, otp }),
  me:           (token: string) =>
    axios.get(`${API_BASE_URL}/auth/me/`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  refreshToken: (refresh: string) =>
    apiClient.post('/auth/token/refresh/', { refresh }),
  exchangeOidc: (idToken: string) =>
    apiClient.post('/auth/oidc/exchange/', { id_token: idToken }),
  logout:       (refresh: string) =>
    apiClient.post('/auth/logout/', { refresh }),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.post('/auth/change-password/', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  redeemBreakGlass: (token: string) =>
    apiClient.get(`/auth/break-glass-redeem/?token=${encodeURIComponent(token)}`),
}

export const configAPI = {
  getConfig: () => apiClient.get('/config/'),
}

export const launcherAPI = {
  getLicensedSystems: () => apiClient.get('/launcher/systems/'),
  initiateSSO:        (system: string) => apiClient.post(`/launcher/sso/${system}/`),
}
