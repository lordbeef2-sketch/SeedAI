import { Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import ChatPage from './pages/ChatPage'
import RagPage from './pages/RagPage'
import SettingsPage from './pages/SettingsPage'
import Sidebar from './components/Sidebar'
import { useChat } from './state/useChat'
import { useSettings } from './state/useSettings'
import { api } from './lib/api'

function App() {
  const { setModels, setError } = useChat()
  const { baseUrl } = useSettings()

  useEffect(() => {
    // Load models on mount
    const loadModels = async () => {
      try {
        const models = await api.getModels()
        setModels(models)
        // Preselect default model if present
  const defaultModel = ((import.meta as any).env?.VITE_DEFAULT_MODEL as string) || 'llama3.2-vision:11b'
        const found = models.find((m: any) => m.id === defaultModel)
        if (found) {
          // set in settings store
          const { setSelectedModel } = useSettings.getState()
          setSelectedModel(found.id)
        } else if (models.length > 0) {
          const { setSelectedModel } = useSettings.getState()
          setSelectedModel(models[0].id)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
        setError('Failed to load models')
      }
    }

    loadModels()
  }, [baseUrl, setModels, setError])

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/rag" element={<RagPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App