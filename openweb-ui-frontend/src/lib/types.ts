export interface Model {
  id: string
  owned_by: string
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  metadata?: {
    emotions?: string[]
    [key: string]: any
  }
}

export interface ChatRequest {
  messages: Message[]
  model?: string | null
  stream?: boolean
  temperature?: number | null
  max_tokens?: number | null
  metadata?: {
    memory_first?: boolean
    llm_permission?: 'always' | 'once' | 'deny'
  }
}

export interface ChatResponse {
  object: 'chat.completion'
  choices: Array<{
    message: Message
  }>
}

export interface EmbeddingRequest {
  input: string[]
  model?: string
}

export interface EmbeddingResponse {
  data: Array<{
    embedding: number[]
    index: number
  }>
}

export interface FileUploadResponse {
  id: string
  filename: string
}

export interface UnknownWord {
  word: string
  count: number
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  created_at: Date
}

export interface RagFile {
  id: string
  filename: string
  size: number
  uploaded_at: Date
}