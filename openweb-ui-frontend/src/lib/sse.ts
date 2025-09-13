import { ChatRequest } from './types'

export interface SSEEvent {
  data: string
  event?: string
  id?: string
}

export class SSEClient {
  private controller: AbortController | null = null
  private retryCount = 0
  private maxRetries = 3
  private retryDelay = 1000

  constructor(
    private url: string,
    private options: RequestInit = {}
  ) {}

  async connect(
    onMessage: (event: SSEEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): Promise<void> {
    this.controller = new AbortController()
    const signal = this.controller.signal

    try {
      const response = await fetch(this.url, {
        ...this.options,
        signal,
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
          ...this.options.headers,
        },
      })

      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (!signal.aborted) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const data = line.slice(5).trim()
            if (data === '[DONE]') {
              onComplete?.()
              return
            }
            onMessage({ data })
          } else if (line.startsWith('event:')) {
            // Handle event type if needed
          } else if (line.startsWith('id:')) {
            // Handle event id if needed
          }
        }
      }

      this.retryCount = 0
    } catch (error) {
      if (signal.aborted) return

      console.warn('SSE error:', error)
      onError?.(error as Error)

      if (this.retryCount < this.maxRetries) {
        this.retryCount++
        setTimeout(() => {
          this.connect(onMessage, onError, onComplete)
        }, this.retryDelay * Math.pow(2, this.retryCount - 1))
      }
    }
  }

  disconnect(): void {
    this.controller?.abort()
    this.controller = null
  }

  isConnected(): boolean {
    return this.controller !== null && !this.controller.signal.aborted
  }
}

export async function chatStream(
  request: ChatRequest,
  onChunk: (chunk: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
  const url = `${baseUrl}/api/chat`

  const sseClient = new SSEClient(url, {
    method: 'POST',
    body: JSON.stringify({ ...request, stream: true }),
    headers: {
      'Content-Type': 'application/json',
    },
  })

  let fullContent = ''

  await sseClient.connect(
    (event) => {
      try {
        const data = JSON.parse(event.data)
        const chunk = data.choices?.[0]?.delta?.content
        if (chunk) {
          fullContent += chunk
          onChunk(fullContent)
        }
      } catch (error) {
        console.warn('Failed to parse SSE data:', error)
      }
    },
    onError,
    onComplete
  )
}