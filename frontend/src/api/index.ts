import axios, { AxiosError, AxiosResponse } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor - handle errors
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    return Promise.reject(error)
  }
)

export default api

// Auth API
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  
  register: (data: { username: string; email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data),
  
  me: () => api.get('/auth/me'),
  
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
}

// Documents API
export const documentsApi = {
  list: (params?: {
    page?: number
    page_size?: number
    status_filter?: string
    search?: string
  }) => api.get('/documents', { params }),
  
  get: (id: string, includeChunks = false) =>
    api.get(`/documents/${id}`, { params: { include_chunks: includeChunks } }),
  
  upload: (file: File, data?: {
    title?: string
    classification?: string
    department_id?: string
    project_id?: string
    tags?: string
  }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (data?.title) formData.append('title', data.title)
    if (data?.classification) formData.append('classification', data.classification)
    if (data?.department_id) formData.append('department_id', data.department_id)
    if (data?.project_id) formData.append('project_id', data.project_id)
    if (data?.tags) formData.append('tags', data.tags)
    
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  delete: (id: string, hardDelete = false) =>
    api.delete(`/documents/${id}`, { params: { hard_delete: hardDelete } }),
  
  download: (id: string) => api.get(`/documents/${id}/download`),
  
  getStatus: (id: string) => api.get(`/documents/${id}/status`),
}

// Search API
export const searchApi = {
  search: (data: {
    query: string
    top_k?: number
    top_n?: number
    use_rerank?: boolean
    use_hybrid?: boolean
    department_id?: string
    project_id?: string
  }) => api.post('/search', data),
  
  quickSearch: (query: string, limit = 5) =>
    api.get('/search/quick', { params: { q: query, limit } }),
}

// Chat API
export const chatApi = {
  chat: (data: {
    query: string
    top_k?: number
    top_n?: number
    use_rerank?: boolean
    use_hybrid?: boolean
    use_query_rewrite?: boolean
    stream?: boolean
  }) => api.post('/chat', data),
  
  chatStream: async function* (data: {
    query: string
    top_k?: number
    top_n?: number
    use_rerank?: boolean
    use_hybrid?: boolean
  }) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...data, stream: true }),
    })
    
    const reader = response.body?.getReader()
    if (!reader) return
    
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          yield data
        }
      }
    }
  },
  
  submitFeedback: (searchLogId: string, helpful: boolean, comment?: string) =>
    api.post('/chat/feedback', { search_log_id: searchLogId, helpful, comment }),
}

// Admin API
export const adminApi = {
  getStats: () => api.get('/admin/stats'),
  
  listUsers: (params?: { page?: number; page_size?: number }) =>
    api.get('/admin/users', { params }),
  
  updateUser: (userId: string, data: {
    role?: string
    department_id?: string
    max_classification?: string
    is_active?: boolean
  }) => api.patch(`/admin/users/${userId}`, data),
  
  getAuditLogs: (params?: {
    page?: number
    page_size?: number
    user_id?: string
    action?: string
  }) => api.get('/admin/audit-logs', { params }),
  
  listDepartments: () => api.get('/admin/departments'),
  
  createDepartment: (data: { name: string; code: string; parent_id?: string }) =>
    api.post('/admin/departments', data),
  
  listProjects: () => api.get('/admin/projects'),
  
  createProject: (data: { name: string; code: string; department_id?: string }) =>
    api.post('/admin/projects', data),
  
  getSearchAnalytics: (days = 7) =>
    api.get('/admin/search-analytics', { params: { days } }),
}
