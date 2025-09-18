export const storage = {
  get: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key)
      if (!item) return defaultValue

      // Some older or corrupt values may be non-JSON (e.g. '[object Object]')
      // Try parsing safely, otherwise return default
      try {
        return JSON.parse(item) as T
      } catch (err) {
        console.warn(`localStorage: failed to parse key '${key}', resetting to default.`)
        return defaultValue
      }
    } catch (err) {
      console.warn('localStorage.get error:', err)
      return defaultValue
    }
  },
  set: <T>(key: string, value: T): void => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.warn('Failed to save to localStorage:', error)
    }
  },
  remove: (key: string): void => {
    try {
      localStorage.removeItem(key)
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error)
    }
  },
}

export const STORAGE_KEYS = {
  SETTINGS: 'openwebui-settings',
  CONVERSATIONS: 'openwebui-conversations',
  RAG_FILES: 'openwebui-rag-files',
} as const