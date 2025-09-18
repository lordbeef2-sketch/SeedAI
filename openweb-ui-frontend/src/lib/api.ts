import { ChatRequest, ChatResponse, Model, EmbeddingRequest, EmbeddingResponse, FileUploadResponse, UnknownWord } from './types'
import { useSettings } from '@/state/useSettings'

const getBaseUrl = () => useSettings.getState().baseUrl

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getBaseUrl()
  const url = `${baseUrl}${endpoint}`

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  async getModels(): Promise<Model[]> {
    try {
      const response = await apiRequest<any>('/api/models')
      // Accept multiple shapes: { data: [...] } or { models: [...] } or an array
      let list: any[] = []
      if (response.data && Array.isArray(response.data)) list = response.data
      else if (response.models && Array.isArray(response.models)) list = response.models
      else if (Array.isArray(response)) list = response
      // Normalize to Model[] with id field
      const models: Model[] = list.map((m) => {
        if (typeof m === 'string') {
          // Try to extract id from python-style or json-style dict string
          const pyIdMatch = m.match(/['\"]id['\"]\s*:\s*['\"]([^'\"]+)['\"]/)
          const jsonIdMatch = m.match(/"id"\s*:\s*"([^"]+)"/)
          const id = (pyIdMatch && pyIdMatch[1]) || (jsonIdMatch && jsonIdMatch[1]) || m
          const pyOwned = m.match(/['\"]owned_by['\"]\s*:\s*['\"]([^'\"]+)['\"]/)
          const owned_by = (pyOwned && pyOwned[1]) || 'library'
          return { id, owned_by }
        }
        if (m && typeof m === 'object') return { id: m.id || m.name || String(m), owned_by: m.owned_by || m.owner || 'library' }
        return { id: String(m), owned_by: 'unknown' }
      })
      return models
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      return await apiRequest<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify(request),
      })
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async embeddings(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    try {
      return await apiRequest<EmbeddingResponse>('/api/embeddings', {
        method: 'POST',
        body: JSON.stringify(request),
      })
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async uploadFile(file: File): Promise<FileUploadResponse> {
    const baseUrl = getBaseUrl()
    const url = `${baseUrl}/api/files`

    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  },

  async getUnknownWords(): Promise<UnknownWord[]> {
    try {
      const response = await apiRequest<{ data: UnknownWord[] }>('/api/unknown_words')
      return response.data
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        // Endpoint not available, return empty array
        return []
      }
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async ackUnknownWord(word: string): Promise<void> {
    try {
      await apiRequest(`/api/unknown_words/ack/${encodeURIComponent(word)}`, {
        method: 'POST',
      })
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async search(query: string): Promise<any> {
    try {
      return await apiRequest('/api/search', {
        method: 'POST',
        body: JSON.stringify({ query }),
      })
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        // Search not implemented
        return null
      }
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },
}

// Lightweight helpers for arbitrary GET/POST calls used by settings persistence
export async function apiGet<T = any>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' })
}

export async function apiPost<T = any>(endpoint: string, body: any): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'POST', body: JSON.stringify(body) })
}