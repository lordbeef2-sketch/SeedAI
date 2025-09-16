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
      const response = await apiRequest<{ data: Model[] }>('/api/models')
      return response.data
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error')
    }
  },

  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      return await apiRequest<ChatResponse>('/api/chat/completions', {
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