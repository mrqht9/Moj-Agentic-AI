import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { FiMenu, FiSun, FiMoon } from 'react-icons/fi'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import logoLight from '../assets/logos/logo-light.png'
import logoDark from '../assets/logos/logo-dark.png'

const ChatInterface = ({ darkMode, setDarkMode, user }) => {
  const logo = darkMode ? logoLight : logoDark
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: 'مرحباً! أنا مساعدك الذكي في Mwj AI. يمكنني مساعدتك في إدارة وسائل التواصل الاجتماعي، التحليلات، والأتمتة. كيف يمكنني مساعدتك اليوم؟',
      timestamp: new Date().toISOString()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [ws, setWs] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const messagesEndRef = useRef(null)
  const inputFocusRef = useRef(null)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const refreshSidebarConversations = () => {
    window.dispatchEvent(new CustomEvent('mwj:conversation_updated'))
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [])

  useEffect(() => {
    const handleNewChat = (e) => {
      const newSessionId = e?.detail?.session_id || `session_${Date.now()}`
      localStorage.setItem('session_id', newSessionId)
      setMessages([{
        id: Date.now(),
        type: 'assistant',
        content: 'مرحباً! أنا مساعدك الذكي في Mwj AI. يمكنني مساعدتك في إدارة وسائل التواصل الاجتماعي، التحليلات، والأتمتة. كيف يمكنني مساعدتك اليوم؟',
        timestamp: new Date().toISOString()
      }])
      setShowSuggestions(true)
      refreshSidebarConversations()
    }

    const handleLoadConversationEvent = async (e) => {
      const conversationId = e?.detail?.conversationId
      if (!conversationId) return
      await handleLoadConversation(conversationId)
    }

    window.addEventListener('mwj:new_chat', handleNewChat)
    window.addEventListener('mwj:load_conversation', handleLoadConversationEvent)
    return () => {
      window.removeEventListener('mwj:new_chat', handleNewChat)
      window.removeEventListener('mwj:load_conversation', handleLoadConversationEvent)
    }
  }, [user])

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/chat`
    
    const websocket = new WebSocket(wsUrl)
    
    websocket.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    }
    
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      setTimeout(connectWebSocket, 3000)
    }
    
    setWs(websocket)
  }

  const handleWebSocketMessage = (data) => {
    if (data.type === 'typing') {
      setIsTyping(data.status)
    } else if (data.type === 'assistant_message') {
      // تجاهل الرسائل الفارغة أو null
      if (data.message && data.message !== null) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          type: 'assistant',
          content: data.message,
          attachment: data.attachment || null,
          timestamp: data.timestamp
        }])
        refreshSidebarConversations()
      }
    } else if (data.type === 'error') {
      // عرض رسالة خطأ عامة إذا كانت الرسالة null
      const errorMessage = data.message || 'حدث خطأ غير متوقع'
      setMessages(prev => [...prev, {
        id: Date.now(),
        type: 'error',
        content: errorMessage,
        timestamp: data.timestamp
      }])
    }
  }

  const handleSendMessage = () => {
    if (!inputValue.trim() || !isConnected) return

    const newMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, newMessage])
    setShowSuggestions(false)
    refreshSidebarConversations()
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      // إرسال الرسالة مع user_id و user_email و session_id
      const messageData = {
        message: inputValue,
        user_id: user?.id || null,
        user_email: user?.email || null,
        session_id: localStorage.getItem('session_id') || `session_${Date.now()}`
      }
      
      // حفظ session_id إذا لم يكن موجوداً
      if (!localStorage.getItem('session_id')) {
        localStorage.setItem('session_id', messageData.session_id)
      }
      
      ws.send(JSON.stringify(messageData))
    }

    setInputValue('')
  }

  const uploadAttachment = async (file) => {
    const form = new FormData()
    form.append('file', file)
    const response = await axios.post(`${API_URL}/api/uploads`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    const data = response.data
    const fullUrl = data.url?.startsWith('http') ? data.url : `${API_URL}${data.url}`

    return {
      kind: data.kind,
      url: data.url,
      url_full: fullUrl,
      original_name: data.original_name,
      size: data.size,
      content_type: data.content_type
    }
  }

  const sendAttachmentMessage = async (file) => {
    if (!isConnected || !ws || ws.readyState !== WebSocket.OPEN) return

    const attachment = await uploadAttachment(file)
    const messageData = {
      message: '',
      attachment,
      user_id: user?.id || null,
      user_email: user?.email || null,
      session_id: localStorage.getItem('session_id') || `session_${Date.now()}`
    }

    if (!localStorage.getItem('session_id')) {
      localStorage.setItem('session_id', messageData.session_id)
    }

    setMessages(prev => [...prev, {
      id: Date.now(),
      type: 'user',
      content: '',
      attachment,
      timestamp: new Date().toISOString()
    }])

    setShowSuggestions(false)

    refreshSidebarConversations()

    ws.send(JSON.stringify(messageData))
  }

  const handleNewChat = () => {
    if (window.confirm('هل تريد بدء محادثة جديدة؟ سيتم حذف المحادثة الحالية.')) {
      setMessages([{
        id: Date.now(),
        type: 'assistant',
        content: 'مرحباً! أنا مساعدك الذكي في Mwj AI. يمكنني مساعدتك في إدارة وسائل التواصل الاجتماعي، التحليلات، والأتمتة. كيف يمكنني مساعدتك اليوم؟',
        timestamp: new Date().toISOString()
      }])
      // إنشاء session_id جديد
      localStorage.setItem('session_id', `session_${Date.now()}`)
      setShowSuggestions(true)
      refreshSidebarConversations()
    }
  }

  const handleSuggestionClick = (text) => {
    setInputValue(text)
    setShowSuggestions(false)
    if (typeof inputFocusRef.current === 'function') {
      inputFocusRef.current()
    }
  }

  const handleLoadConversation = async (conversationId) => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get(
        `${API_URL}/api/conversations/${conversationId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      const payload = response.data
      const msgs = payload?.messages || payload?.conversation?.messages || payload?.conversation_detail?.messages
      const conv = payload?.conversation || payload?.conversation_detail?.conversation

      if (Array.isArray(msgs)) {
        // تحويل الرسائل إلى التنسيق المطلوب
        const loadedMessages = msgs.map(msg => ({
          id: msg.id,
          type: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
          attachment: msg.attachment || null,
          timestamp: msg.created_at
        }))
        
        setMessages(loadedMessages)
        
        // تحديث session_id للمحادثة المحملة
        localStorage.setItem('session_id', conv?.session_id || payload?.session_id || `session_${conversationId}`)
        refreshSidebarConversations()
      }
    } catch (error) {
      console.error('Failed to load conversation:', error)
      alert('فشل تحميل المحادثة')
    }
  }

  return (
      <main className="flex-1 flex flex-col h-full bg-background-light dark:bg-background-dark relative">
        <div className="flex flex-col">
          {/* Header */}
          <header className="relative flex items-center justify-between px-6 py-5 min-h-[64px] shrink-0 bg-card-light dark:bg-sidebar-dark z-10">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="absolute left-6 top-1/2 -translate-y-1/2 flex items-center justify-center rounded-xl size-10 hover:bg-gray-50 dark:hover:bg-card-dark text-text-secondary-light dark:text-text-secondary-dark transition-colors"
              title="تبديل المظهر"
            >
              {darkMode ? <FiSun size={20} /> : <FiMoon size={20} />}
            </button>
            <div className="flex items-center gap-2">
              <button className="flex items-center justify-center rounded-xl size-10 hover:bg-gray-50 dark:hover:bg-card-dark text-text-secondary-light dark:text-text-secondary-dark transition-colors md:hidden">
                <FiMenu size={20} />
              </button>
            </div>
            <div className="flex items-center gap-3 text-text-primary-light dark:text-text-primary-dark">
            </div>
          </header>

          {/* فاصل أفقي تحت Header - يمتد بعرض كامل */}
          <div className="h-px bg-border-light dark:bg-border-dark w-full"></div>
        </div>

        {/* Messages */}
        <MessageList 
          messages={messages}
          isTyping={isTyping}
          messagesEndRef={messagesEndRef}
          showSuggestions={showSuggestions}
          onSuggestionClick={handleSuggestionClick}
        />

        {/* Input */}
        <MessageInput 
          inputValue={inputValue}
          setInputValue={setInputValue}
          handleSendMessage={handleSendMessage}
          isConnected={isConnected}
          onAttachImage={sendAttachmentMessage}
          onAttachFile={sendAttachmentMessage}
          onFocusRef={inputFocusRef}
        />
      </main>
  )
}

export default ChatInterface
