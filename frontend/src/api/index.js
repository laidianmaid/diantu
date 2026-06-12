import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          err.config.headers.Authorization = `Bearer ${data.access_token}`
          return api(err.config)
        } catch {
          localStorage.clear()
        }
      }
    }
    return Promise.reject(err)
  }
)

export const shopApi = {
  list: (params) => api.get('/shops', { params }),
  get: (id) => api.get(`/shops/${id}`),
  create: (data) => api.post('/shops', data),
  update: (id, data) => api.patch(`/shops/${id}`, data),
  delete: (id) => api.delete(`/shops/${id}`),
  favorite: (id) => api.post(`/shops/${id}/favorite`),
  checkin: (id) => api.post(`/shops/${id}/checkin`),
  importMarkdown: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/shops/admin/import/markdown', form)
  },
}

export const reviewApi = {
  list: (shopId) => api.get(`/shops/${shopId}/reviews`),
  create: (shopId, data) => api.post(`/shops/${shopId}/reviews`, data),
  delete: (id) => api.delete(`/reviews/${id}`),
  react: (id, type) => api.post(`/reviews/${id}/reactions`, { type }),
}

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/users/me'),
  generateApiKey: () => api.post('/users/me/apikey'),
}

export const aiApi = {
  chat: (payload) => api.post('/ai/chat', payload),
  agentConfig: () => api.get('/ai/agent/config'),
  executeTool: (payload) => api.post('/ai/tools/execute', payload),
}

export default api
