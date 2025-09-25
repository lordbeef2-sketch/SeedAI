import { useSettings } from '@/state/useSettings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import React from 'react'

const SettingsPage = () => {
  const {
    baseUrl,
    sseEnabled,
    setBaseUrl,
    setSseEnabled,
    reset,
  } = useSettings()

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      reset()
    }
  }

  const [personaText, setPersonaText] = React.useState('')

  const savePersona = async () => {
    try {
      const base = (window as any).__SEEDAI_BASE_URL__ || ''
      const res = await fetch(`${base}/api/persona/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona: personaText }),
      })
      const j = await res.json()
      console.debug('persona save response', j)
      if (!res.ok) alert('Failed to save persona: ' + (j.detail || res.status))
      else alert('Persona saved — bytes: ' + j.bytes)
    } catch (err) {
      console.error(err)
      alert('Error saving persona — see console')
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-background p-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Configure your OpenWebUI preferences
          </p>
        </div>
      </div>

      {/* Settings */}
      <div className="flex-1 p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* API Settings */}
          <div className="space-y-4">
            <h2 className="text-lg font-medium">API Configuration</h2>

            <div className="space-y-2">
              <label htmlFor="base-url" className="text-sm font-medium">Base URL</label>
              <Input
                id="base-url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://localhost:8080"
              />
              <p className="text-sm text-muted-foreground">
                URL of your SeedAI backend server
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="sse-enabled"
                checked={sseEnabled}
                onCheckedChange={setSseEnabled}
              />
              <label htmlFor="sse-enabled" className="text-sm font-medium">Enable SSE Streaming</label>
            </div>
            <p className="text-sm text-muted-foreground">
              Enable real-time streaming responses (recommended)
            </p>
          </div>

          {/* UI Settings */}
          <div className="space-y-4">
            <h2 className="text-lg font-medium">Interface</h2>

            <div className="space-y-2">
              <label className="text-sm font-medium">Theme</label>
              <div className="text-sm text-muted-foreground">
                Theme switching will be available in future updates
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="pt-6 border-t">
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Button variant="outline" onClick={handleReset}>
                  Reset to Defaults
                </Button>
              </div>

              <div className="pt-4">
                <label className="text-sm font-medium">Persona (debug)</label>
                <textarea
                  className="w-full h-40 p-2 border rounded"
                  value={personaText}
                  onChange={(e) => setPersonaText(e.target.value)}
                  placeholder="Paste persona markdown here"
                />
                <div className="pt-2">
                  <Button onClick={savePersona}>Save Persona (debug)</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage