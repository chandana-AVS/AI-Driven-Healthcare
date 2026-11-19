import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Access tokens are short-lived (30 min) and kept in memory, mirrored to sessionStorage so a page refresh
// keeps the session. sessionStorage is cleared when the tab closes; nothing is written to localStorage.
const TOKEN_KEY = 'hc_access_token'
let accessToken = sessionStorage.getItem(TOKEN_KEY)

export const tokenStore = {
  get: () => accessToken,
  set: (token) => {
    accessToken = token
    if (token) sessionStorage.setItem(TOKEN_KEY, token)
    else sessionStorage.removeItem(TOKEN_KEY)
  },
}

const api = axios.create({ baseURL: API_BASE_URL, timeout: 30000 })

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const isLogin = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isLogin && accessToken) {
      tokenStore.set(null)
      onUnauthorized(error.response.data?.detail)
    }
    return Promise.reject(error)
  },
)

/** Turn any API error into a readable message (handles FastAPI validation errors). */
export function errorMessage(err, fallback = 'Something went wrong. Please try again.') {
  if (!err?.response) return err?.message === 'Network Error' ? 'Cannot reach the server. Is the backend running?' : fallback
  const data = err.response.data
  if (Array.isArray(data?.errors) && data.errors.length) {
    return data.errors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message)).join(' • ')
  }
  if (typeof data?.detail === 'string') return data.detail
  return fallback
}

// ------------------------------------------------------------------ endpoints
export const authApi = {
  registerPatient: (data) => api.post('/auth/register/patient', data),
  registerWorker: (data) => api.post('/auth/register/healthcare-worker', data),
  registerAdmin: (data) => api.post('/auth/register/admin', data),
  login: (identifier, password) => api.post('/auth/login', { identifier, password }),
  sendOtp: (identifier) => api.post('/auth/phone/send-otp', { identifier }),
  verifyPhone: (identifier, code) => api.post('/auth/phone/verify', { identifier, code }),
}

export const userApi = {
  me: () => api.get('/users/me'),
  update: (data) => api.patch('/users/me', data),
  updateLanguage: (preferred_language) => api.patch('/users/me/language', { preferred_language }),
  languages: () => api.get('/languages'),
}

export const patientApi = {
  me: () => api.get('/patients/me'),
  updateProfile: (data) => api.patch('/patients/me', data),
  documents: (params) => api.get('/patients/me/documents', { params }),
  upload: (formData, onUploadProgress) => api.post('/patients/me/documents', formData, { onUploadProgress }),
  records: () => api.get('/patients/me/records'),
  history: () => api.get('/patients/me/history'),
  accessList: () => api.get('/patients/me/access'),
  grantAccess: (data) => api.post('/patients/me/access', data),
  revokeAccess: (grantId) => api.delete(`/patients/me/access/${grantId}`),
  workerDirectory: (search) => api.get('/patients/me/workers', { params: { search } }),
  // patient-specific routes (used by authorized healthcare workers)
  documentsOf: (patientId, params) => api.get(`/patients/${patientId}/documents`, { params }),
  uploadFor: (patientId, formData, onUploadProgress) =>
    api.post(`/patients/${patientId}/documents`, formData, { onUploadProgress }),
  recordsOf: (patientId) => api.get(`/patients/${patientId}/records`),
  createRecord: (patientId, data) => api.post(`/patients/${patientId}/records`, data),
  historyOf: (patientId) => api.get(`/patients/${patientId}/history`),
}

export const workerApi = {
  me: () => api.get('/healthcare-workers/me'),
  update: (data) => api.patch('/healthcare-workers/me', data),
  patients: () => api.get('/healthcare-workers/me/patients'),
}

export const documentApi = {
  get: (id) => api.get(`/documents/${id}`),
  remove: (id) => api.delete(`/documents/${id}`),
  /** Download with the auth header, then save via a temporary object URL. */
  download: async (doc) => {
    const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.document_name
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
  /** Fetch the file with the auth header and return a temporary object URL (caller must revoke it). */
  objectUrl: async (doc) => {
    const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' })
    return URL.createObjectURL(new Blob([res.data], { type: doc.mime_type }))
  },
  /** Open in a new tab for viewing (PDF/images). */
  view: async (doc) => {
    const win = window.open('', '_blank')
    const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: doc.mime_type }))
    if (win) win.location.href = url
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  },
}

export const contentApi = {
  list: (params) => api.get('/content', { params }),
  translations: (id) => api.get(`/content/${id}/translations`),
  get: (id) => api.get(`/content/${id}`),
  categories: () => api.get('/content/categories'),
}

export const adminApi = {
  me: () => api.get('/admin/me'),
  setAdminVerification: (adminProfileId, verification_status) =>
    api.patch(`/admin/admins/${adminProfileId}/verification`, { verification_status }),
  stats: () => api.get('/admin/stats'),
  users: (params) => api.get('/admin/users', { params }),
  setUserStatus: (id, is_active) => api.patch(`/admin/users/${id}/status`, { is_active }),
  setVerification: (workerId, verification_status) =>
    api.patch(`/admin/healthcare-workers/${workerId}/verification`, { verification_status }),
  content: (params) => api.get('/admin/content', { params }),
  createContent: (data) => api.post('/admin/content', data),
  updateContent: (id, data) => api.patch(`/admin/content/${id}`, data),
  deleteContent: (id) => api.delete(`/admin/content/${id}`),
  access: () => api.get('/admin/access'),
  grantAccess: (data) => api.post('/admin/access', data),
  revokeAccess: (id) => api.delete(`/admin/access/${id}`),
  auditLogs: (params) => api.get('/admin/audit-logs', { params }),
  translateContent: (id, languages) => api.post(`/admin/content/${id}/translate`, { languages }, { timeout: AI_TIMEOUT }),
}

// ------------------------------------------------------------------ Milestone 2: AI language engine
const AI_TIMEOUT = 180000

export const aiApi = {
  status: () => api.get('/ai/status'),
  translate: (data) => api.post('/ai/translate', data, { timeout: AI_TIMEOUT }),
  simplify: (data) => api.post('/ai/simplify', data, { timeout: AI_TIMEOUT }),
  extract: (data) => api.post('/ai/extract', data, { timeout: AI_TIMEOUT }),
  symptoms: (data) => api.post('/ai/symptoms', data, { timeout: AI_TIMEOUT }),
  analyzeDocument: (id, language, force = false) => api.post(`/documents/${id}/analysis`, { language, force }),
  documentAnalysis: (id, language) => api.get(`/documents/${id}/analysis`, { params: { language } }),
  documentAnalyses: (id) => api.get(`/documents/${id}/analyses`),
}

export default api
