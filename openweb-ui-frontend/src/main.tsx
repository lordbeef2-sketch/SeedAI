import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from '@/components/ui/toast'
import App from './App.tsx'
import './styles/globals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
      <Toaster />
    </BrowserRouter>
  </StrictMode>,
)

// Dev helper: expose the Zustand useSettings store to window for manual debugging
// Usage (in DevTools): window.__USE_SETTINGS__.setBaseUrl('http://127.0.0.1:8090')
if ((import.meta as any).env?.DEV) {
  try {
    // Lazy-import to avoid bundling in production
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { useSettings } = require('./state/useSettings')
    // Attach a minimal API that mirrors the store setters
    ;(window as any).__USE_SETTINGS__ = {
      getState: () => useSettings.getState(),
      setBaseUrl: (url: string) => useSettings.getState().setBaseUrl(url),
      setSseEnabled: (v: boolean) => useSettings.getState().setSseEnabled(v),
      setSelectedModel: (m: string) => useSettings.getState().setSelectedModel(m),
      setTemperature: (t: number) => useSettings.getState().setTemperature(t),
      setMemoryFirst: (v: boolean) => useSettings.getState().setMemoryFirst(v),
      setLlmPermission: (p: any) => useSettings.getState().setLlmPermission(p),
      reset: () => useSettings.getState().reset(),
    }
    // eslint-disable-next-line no-console
    console.log('Dev: window.__USE_SETTINGS__ available')
  } catch (err) {
    // ignore in case require is unavailable in the bundler environment
  }
}