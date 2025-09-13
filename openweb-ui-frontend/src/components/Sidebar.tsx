import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { MessageSquare, FileText, Settings, Menu, X } from 'lucide-react'
import { useChat } from '@/state/useChat'
import { Button } from '@/components/ui/button'

const Sidebar = () => {
  const [isOpen, setIsOpen] = useState(false)
  const location = useLocation()
  const { conversations, createConversation, setActiveConversation } = useChat()

  const navigation = [
    { name: 'Chat', href: '/chat', icon: MessageSquare },
    { name: 'RAG', href: '/rag', icon: FileText },
    { name: 'Settings', href: '/settings', icon: Settings },
  ]

  const handleNewChat = () => {
    createConversation()
    setIsOpen(false)
  }

  return (
    <>
      {/* Mobile menu button */}
      <div className="md:hidden fixed top-4 left-4 z-50">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      </div>

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-card border-r transform transition-transform duration-200 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:static md:inset-0
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b">
            <h1 className="text-xl font-bold">OpenWebUI</h1>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            <Button
              onClick={handleNewChat}
              className="w-full justify-start"
              variant="outline"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              New Chat
            </Button>

            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link key={item.name} to={item.href}>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    className="w-full justify-start"
                    onClick={() => setIsOpen(false)}
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {item.name}
                  </Button>
                </Link>
              )
            })}
          </nav>

          {/* Conversations */}
          <div className="p-4 border-t">
            <h3 className="text-sm font-medium mb-2">Recent Chats</h3>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {conversations.slice(0, 10).map((conv) => (
                <Button
                  key={conv.id}
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-left h-auto py-2 px-3"
                  onClick={() => {
                    setActiveConversation(conv.id)
                    setIsOpen(false)
                  }}
                >
                  <span className="truncate block">{conv.title}</span>
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}

export default Sidebar