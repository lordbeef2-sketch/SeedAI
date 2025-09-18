import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { STORAGE_KEYS, storage } from '@/lib/storage'
import { Message, Conversation, Model } from '@/lib/types'

interface ChatState {
  conversations: Conversation[]
  activeConversationId: string | null
  models: Model[]
  isLoading: boolean
  error: string | null
  streamingMessage: string
  isStreaming: boolean

  // Actions
  setActiveConversation: (id: string) => void
  createConversation: () => void
  addMessage: (message: Message) => void
  updateStreamingMessage: (content: string) => void
  finalizeStreamingMessage: () => void
  setModels: (models: Model[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  deleteConversation: (id: string) => void
  clearConversations: () => void
}

const defaultState: Omit<ChatState, 'setActiveConversation' | 'createConversation' | 'addMessage' | 'updateStreamingMessage' | 'finalizeStreamingMessage' | 'setModels' | 'setLoading' | 'setError' | 'deleteConversation' | 'clearConversations'> = {
  conversations: [],
  activeConversationId: null,
  models: [],
  isLoading: false,
  error: null,
  streamingMessage: '',
  isStreaming: false,
}

export const useChat = create<ChatState>()(
  persist(
    (set, get) => ({
      ...defaultState,

      setActiveConversation: (id) => set({ activeConversationId: id }),

      createConversation: () => {
        const newConversation: Conversation = {
          id: Date.now().toString(),
          title: 'New Chat',
          messages: [],
          created_at: new Date(),
        }
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          activeConversationId: newConversation.id,
        }))
      },

      addMessage: (message) => {
        const state = get()
        if (!state.activeConversationId) return

        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === state.activeConversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message],
                  title: conv.messages.length === 0 && message.role === 'user'
                    ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                    : conv.title,
                }
              : conv
          ),
        }))
      },

      updateStreamingMessage: (content) => {
        set({ streamingMessage: content, isStreaming: true })
      },

      finalizeStreamingMessage: () => {
        const state = get()
        if (!state.activeConversationId || !state.streamingMessage) return

        const assistantMessage: Message = {
          role: 'assistant',
          content: state.streamingMessage,
        }

        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === state.activeConversationId
              ? { ...conv, messages: [...conv.messages, assistantMessage] }
              : conv
          ),
          streamingMessage: '',
          isStreaming: false,
        }))
      },

      setModels: (models) => set({ models }),

      setLoading: (loading) => set({ isLoading: loading }),

      setError: (error) => set({ error }),

      deleteConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          activeConversationId: state.activeConversationId === id ? null : state.activeConversationId,
        }))
      },

      clearConversations: () => set(defaultState),
    }),
    {
      name: STORAGE_KEYS.CONVERSATIONS,
      storage: ({
  getItem: (name: string) => {
          const value = storage.get(name, null)
          try {
            return value ? JSON.stringify(value) : null
          } catch (err) {
            console.warn('useChat.getItem: failed to stringify stored value', err)
            return null
          }
        },
  setItem: (name: string, value: string) => {
          try {
            if (typeof value === 'string') {
              storage.set(name, JSON.parse(value))
            } else {
              storage.set(name, value as any)
            }
          } catch (err) {
            console.warn('useChat.setItem: invalid JSON value, ignoring.', err)
          }
        },
  removeItem: (name: string) => {
          storage.remove(name)
        },
      } as any),
      partialize: (state) => ({
        conversations: state.conversations,
        activeConversationId: state.activeConversationId,
      }),
    }
  )
)