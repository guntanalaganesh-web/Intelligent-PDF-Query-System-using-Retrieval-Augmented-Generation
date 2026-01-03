import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add user ID to all requests (simplified auth)
api.interceptors.request.use((config) => {
  const userId = localStorage.getItem('userId') || 'default-user';
  config.headers['X-User-ID'] = userId;
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || 'An error occurred';
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

// Document APIs
export const documentApi = {
  upload: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress?.(progress);
      },
    });
    return response.data;
  },

  list: async (page = 1, perPage = 20) => {
    const response = await api.get('/documents', { params: { page, per_page: perPage } });
    return response.data;
  },

  get: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  delete: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },

  query: async (documentId, query) => {
    const response = await api.post(`/documents/${documentId}/query`, { query });
    return response.data;
  },

  queryStream: async function* (documentId, query) {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': localStorage.getItem('userId') || 'default-user',
      },
      body: JSON.stringify({ query }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          yield data;
        }
      }
    }
  },
};

// Conversation APIs
export const conversationApi = {
  create: async (documentId, title) => {
    const response = await api.post(`/documents/${documentId}/conversations`, { title });
    return response.data;
  },

  list: async (documentId) => {
    const response = await api.get('/conversations', { params: { document_id: documentId } });
    return response.data;
  },

  get: async (conversationId) => {
    const response = await api.get(`/conversations/${conversationId}`);
    return response.data;
  },

  sendMessage: async (conversationId, message) => {
    const response = await api.post(`/conversations/${conversationId}/messages`, { message });
    return response.data;
  },
};

// Search APIs
export const searchApi = {
  search: async (query, documentIds = [], k = 10) => {
    const response = await api.post('/search', { query, document_ids: documentIds, k });
    return response.data;
  },
};

// Analytics APIs
export const analyticsApi = {
  getUsage: async () => {
    const response = await api.get('/analytics/usage');
    return response.data;
  },
};

export default api;
