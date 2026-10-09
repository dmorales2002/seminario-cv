const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

async function request(path, options = {}) {
  const token = localStorage.getItem('expediente_token')
  const headers = new Headers(options.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    let detail = 'No fue posible completar la solicitud.'
    try { detail = (await response.json()).detail || detail } catch { /* empty response */ }
    throw new ApiError(Array.isArray(detail) ? detail.map(x => x.msg).join(', ') : detail, response.status)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  login: async (email, password) => {
    const body = new URLSearchParams({ username: email, password })
    return request('/auth/login', { method: 'POST', body, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
  },
  register: payload => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => request('/users/me'),
  vacancies: () => request('/vacancies/'),
  myVacancies: () => request('/vacancies/my'),
  createVacancy: payload => request('/vacancies/', { method: 'POST', body: JSON.stringify(payload) }),
  updateVacancy: (id, payload) => request(`/vacancies/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  closeVacancy: id => request(`/vacancies/${id}`, { method: 'DELETE' }),
  applications: vacancyId => request(`/applications/${vacancyId}`),
  myApplications: () => request('/applications/my/list'),
  apply: (vacancyId, file) => {
    const body = new FormData(); body.append('cv_file', file)
    return request(`/applications/${vacancyId}`, { method: 'POST', body })
  },
  decide: (vacancyId, applicationId, status) => request(`/applications/${vacancyId}/${applicationId}`, {
    method: 'PATCH', body: JSON.stringify({ status }),
  }),
  extractCriteria: vacancyId => request(`/analysis/vacancies/${vacancyId}/criteria`, { method: 'POST' }),
  getCriteria: vacancyId => request(`/analysis/vacancies/${vacancyId}/criteria`),
  updateCriteria: (vacancyId, criteria) => request(`/analysis/vacancies/${vacancyId}/criteria`, {
    method: 'PUT', body: JSON.stringify({ criteria }),
  }),
  runAnalysis: vacancyId => request(`/analysis/vacancies/${vacancyId}/run`, { method: 'POST' }),
  resumeUrl: (vacancyId, applicationId) => `${API_URL}/applications/${vacancyId}/${applicationId}/resume`,
  async openResume(vacancyId, applicationId) {
    const token = localStorage.getItem('expediente_token')
    const response = await fetch(this.resumeUrl(vacancyId, applicationId), { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new ApiError('No fue posible abrir el currículum.', response.status)
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  },
  async downloadHarvardResume(vacancyId, applicationId) {
    const token = localStorage.getItem('expediente_token')
    const response = await fetch(`${API_URL}/applications/${vacancyId}/${applicationId}/resume/harvard`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      let detail = 'No fue posible descargar el CV Harvard.'
      try { detail = (await response.json()).detail || detail } catch { /* empty */ }
      throw new ApiError(detail, response.status)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `CV_Harvard_${applicationId.slice(0, 8).toUpperCase()}.pdf`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  },
}
