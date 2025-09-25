import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { STORAGE_KEYS, storage } from '@/lib/storage'
import { apiGet, apiPost } from '@/lib/api'

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
  baseUrl: ((import.meta as any).env?.VITE_API_BASE_URL as string) || 'http://127.0.0.1:8090',
  sseEnabled: false,
  selectedModel: 'llama3:13b',
  temperature: 0.7,
  memoryFirst: true,
  llmPermission: 'once',
}

export const useSettings = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...defaultSettings,
      _loadedFromServer: false,
      setBaseUrl: (url) => {
        set({ baseUrl: url })
        try {
          apiPost('/api/settings', { settings: { baseUrl: url } }).catch(() => {})
        } catch (_) {}
      },
      setSseEnabled: (enabled) => {
        set({ sseEnabled: enabled })
        try {
          apiPost('/api/settings', { settings: { sseEnabled: enabled } }).catch(() => {})
        } catch (_) {}
      },
      setSelectedModel: (model) => {
        set({ selectedModel: model })
        try {
          apiPost('/api/settings', { settings: { selectedModel: model } }).catch(() => {})
        } catch (_) {}
      },
      setTemperature: (temp) => {
        set({ temperature: temp })
        try {
          apiPost('/api/settings', { settings: { temperature: temp } }).catch(() => {})
        } catch (_) {}
      },
      setMemoryFirst: (enabled) => {
        set({ memoryFirst: enabled })
        try {
          apiPost('/api/settings', { settings: { memoryFirst: enabled } }).catch(() => {})
        } catch (_) {}
      },
      setLlmPermission: (permission) => {
        set({ llmPermission: permission })
        try {
          apiPost('/api/settings', { settings: { llmPermission: permission } }).catch(() => {})
        } catch (_) {}
      },
      reset: () => {
        set(defaultSettings)
        try {
          apiPost('/api/settings', { settings: defaultSettings }).catch(() => {})
        } catch (_) {}
      },
    }),
    {
      name: STORAGE_KEYS.SETTINGS,
      storage: ({
        getItem: (name: string) => {
          const value = storage.get(name, null)
          try {
            return value ? JSON.stringify(value) : null
          } catch (err) {
            console.warn('useSettings.getItem: failed to stringify stored value', err)
            return null
          }
        },
        setItem: (name: string, value: string) => {
          try {
            if (typeof value === 'string') {
              const parsed = JSON.parse(value)
              storage.set(name, parsed)
            } else {
              storage.set(name, value as any)
            }
          } catch (err) {
            console.warn('useSettings.setItem: invalid JSON value, ignoring.', err)
          }
        },
        removeItem: (name: string) => {
          storage.remove(name)
        },
      } as any),
      // Bootstrap: fetch server-side persisted settings (if available) and merge.
      migrate: async (persistedState: any) => {
        if (!persistedState) persistedState = {}
        const defaultBase = defaultSettings.baseUrl
        try {
          try {
            const resp = await apiGet('/api/settings')
            if (resp && resp.settings) {
              persistedState = { ...persistedState, ...resp.settings }
            }
          } catch (e) {
            // ignore, keep persisted/local
          }

          const s = persistedState as any
          if (!s.baseUrl || typeof s.baseUrl !== 'string') {
            s.baseUrl = defaultBase
          } else {
            // Normalize baseUrl: if user previously set a value ending with '/api' (old VITE_API_URL
            // behavior), strip the trailing '/api' so endpoints like '/api/models' don't become
            // '/api/api/models'. Also guard against dev port misconfigs (e.g., 8088).
            try {
              s.baseUrl = String(s.baseUrl).replace(/\/api\/?$/i, '')
            } catch (_) {
              s.baseUrl = defaultBase
            }
            if (s.baseUrl.includes('8088')) {
              s.baseUrl = defaultBase
            }
          }
          return s
        } catch (err) {
          console.warn('useSettings.migrate: error validating persisted state, resetting to defaults', err)
          return null
        }
      },
      onRehydrateStorage: () => (state, error) => {
        if (error) return
        try {
          // Push current settings to server (best-effort)
          apiPost('/api/settings', { settings: (state as any) }).catch(() => {})
        } catch (e) {
          // noop
        }
      },
    }
  )
)