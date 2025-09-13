import { useState, useRef, KeyboardEvent } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { useChat } from '@/state/useChat'
import { useSettings } from '@/state/useSettings'
import { api } from '@/lib/api'
import { chatStream } from '@/lib/sse'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Modal } from '@/components/Modal'

export const ChatComposer = () => {
  const [input, setInput] = useState('')
  const [showPermissionModal, setShowPermissionModal] = useState(false)
  const [permissionMessage, setPermissionMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { activeConversationId, addMessage, updateStreamingMessage, finalizeStreamingMessage, isLoading, setLoading } = useChat()
  const { selectedModel, temperature, memoryFirst, sseEnabled, setTemperature, setMemoryFirst } = useSettings()

  const handleSubmit = async () => {
    if (!input.trim() || !activeConversationId || isLoading) return

    const userMessage = { role: 'user' as const, content: input.trim() }
    addMessage(userMessage)
    setInput('')
    setLoading(true)

    const messages = [...(useChat.getState().conversations.find(c => c.id === activeConversationId)?.messages || []), userMessage]

    try {
      if (sseEnabled) {
        await chatStream(
          {
            messages,
            model: selectedModel,
            temperature,
            metadata: { memory_first: memoryFirst }
          },
          (chunk) => updateStreamingMessage(chunk),
          (error) => {
            console.error('Streaming error:', error)
            setLoading(false)
          },
          () => {
            finalizeStreamingMessage()
            setLoading(false)
          }
        )
      } else {
        const response = await api.chat({
          messages,
          model: selectedModel,
          stream: false,
          temperature,
          metadata: { memory_first: memoryFirst }
        })

        const assistantMessage = response.choices[0].message
        addMessage(assistantMessage)
        setLoading(false)

        // Check for permission request
        if (assistantMessage.content.toLowerCase().includes('permission to use llm')) {
          setPermissionMessage(assistantMessage.content)
          setShowPermissionModal(true)
        }
      }
    } catch (error) {
      console.error('Chat error:', error)
      setLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handlePermissionResponse = async (allow: boolean) => {
    setShowPermissionModal(false)

    if (!activeConversationId) return

    const messages = useChat.getState().conversations.find(c => c.id === activeConversationId)?.messages || []

    try {
      setLoading(true)
      const response = await api.chat({
        messages,
        model: selectedModel,
        stream: false,
        temperature,
        metadata: {
          memory_first: memoryFirst,
          llm_permission: allow ? 'once' : 'deny'
        }
      })

      addMessage(response.choices[0].message)
    } catch (error) {
      console.error('Permission response error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-t bg-background p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm">Memory First</label>
              <Switch checked={memoryFirst} onCheckedChange={setMemoryFirst} />
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-sm">Temperature: {temperature.toFixed(1)}</label>
              <Slider
                value={[temperature]}
                onValueChange={([value]) => setTemperature(value)}
                min={0}
                max={1}
                step={0.1}
                className="w-24"
              />
            </div>
          </div>
        </div>

        {/* Input */}
        <div className="flex space-x-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 resize-none"
            rows={3}
          />
          <Button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="self-end"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <Modal
        isOpen={showPermissionModal}
        onClose={() => setShowPermissionModal(false)}
        title="LLM Permission Required"
      >
        <div className="space-y-4">
          <p className="text-sm">{permissionMessage}</p>
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => handlePermissionResponse(false)}>
              Deny
            </Button>
            <Button onClick={() => handlePermissionResponse(true)}>
              Allow Once
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}