import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('financial-auth')
  if (token) {
    const authData = JSON.parse(token)
    if (authData.state?.accessToken) {
      config.headers.Authorization = `Bearer ${authData.state.accessToken}`
    }
  }
  return config
})

export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login/', { email, password }),
  verifyOTP: (userId: string, otp: string) =>
    apiClient.post('/auth/verify-otp/', { user_id: userId, otp }),
  me: (token: string) =>
    axios.get(`${API_BASE_URL}/auth/me/`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  refreshToken: (refresh: string) =>
    apiClient.post('/auth/token/refresh/', { refresh }),
  exchangeOidc: (idToken: string) =>
    apiClient.post('/auth/oidc/exchange/', { id_token: idToken }),
}

export const configAPI = {
  getConfig: () => apiClient.get('/config/'),
}

export const launcherAPI = {
  getLicensedSystems: () => apiClient.get('/launcher/systems/'),
  initiateSSO: (system: string) => apiClient.post(`/launcher/sso/${system}/`),
}
