import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, User, Bot } from 'lucide-react'
import { useChat } from '@/state/useChat'
import { useSettings } from '@/state/useSettings'
import { ChatComposer } from '@/components/ChatComposer'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const MessageItem = ({ message, isStreaming = false }: { message: any, isStreaming?: boolean }) => {
  const isUser = message.role === 'user'

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-3xl ${isUser ? 'order-2' : 'order-1'}`}>
        <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          <div className={`p-2 rounded-full ${isUser ? 'bg-primary' : 'bg-secondary'}`}>
            {isUser ? <User className="h-4 w-4 text-primary-foreground" /> : <Bot className="h-4 w-4" />}
          </div>
          <div className={`p-3 rounded-lg ${isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
                {isStreaming && <span className="animate-pulse">▊</span>}
              </div>
            )}
            {!isUser && !isStreaming && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 h-6 px-2"
                onClick={() => copyToClipboard(message.content)}
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy
              </Button>
            )}
          </div>
        </div>
        {/* Emotions badges */}
        {message.metadata?.emotions && (
          <div className="flex flex-wrap gap-1 mt-2 ml-11">
            {message.metadata.emotions.map((emotion: string) => (
              <span key={emotion} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                {emotion}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const ChatPage = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { conversations, activeConversationId, models, streamingMessage, isStreaming } = useChat()
  const { selectedModel, setSelectedModel } = useSettings()

  const activeConversation = conversations.find(c => c.id === activeConversationId)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeConversation?.messages, streamingMessage])

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-background p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold">Chat</h1>
          <div className="flex items-center space-x-2">
            <label className="text-sm">Model:</label>
            <Select value={selectedModel} onValueChange={handleModelChange}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    {model.id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto">
          {activeConversation?.messages.map((message, index) => (
            <MessageItem key={index} message={message} />
          ))}
          {isStreaming && streamingMessage && (
            <MessageItem message={{ role: 'assistant', content: streamingMessage }} isStreaming />
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Composer */}
      <ChatComposer />
    </div>
  )
}

export default ChatPage