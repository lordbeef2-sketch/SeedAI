import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { STORAGE_KEYS, storage } from '@/lib/storage'

interface Settings {
  baseUrl: string
  sseEnabled: boolean
  selectedModel: string
  temperature: number
  memoryFirst: boolean
  llmPermission: 'always' | 'once' | 'deny'
}

interface SettingsState extends Settings {
  setBaseUrl: (url: string) => void
  setSseEnabled: (enabled: boolean) => void
  setSelectedModel: (model: string) => void
  setTemperature: (temp: number) => void
  setMemoryFirst: (enabled: boolean) => void
  setLlmPermission: (permission: 'always' | 'once' | 'deny') => void
  reset: () => void
}

const defaultSettings: Settings = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8088',
  sseEnabled: true,
  selectedModel: 'llama3:13b',
  temperature: 0.7,
  memoryFirst: true,
  llmPermission: 'once',
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultSettings,
      setBaseUrl: (url) => set({ baseUrl: url }),
      setSseEnabled: (enabled) => set({ sseEnabled: enabled }),
      setSelectedModel: (model) => set({ selectedModel: model }),
      setTemperature: (temp) => set({ temperature: temp }),
      setMemoryFirst: (enabled) => set({ memoryFirst: enabled }),
      setLlmPermission: (permission) => set({ llmPermission: permission }),
      reset: () => set(defaultSettings),
    }),
    {
      name: STORAGE_KEYS.SETTINGS,
      storage: {
        getItem: (name) => {
          const value = storage.get(name, null)
          return value ? JSON.stringify(value) : null
        },
        setItem: (name, value) => {
          storage.set(name, JSON.parse(value))
        },
        removeItem: (name) => {
          storage.remove(name)
        },
      },
    }
  )
)