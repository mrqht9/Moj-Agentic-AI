import { FiCopy, FiRefreshCw, FiThumbsUp, FiThumbsDown } from 'react-icons/fi'

const Message = ({ message }) => {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  const formatMessage = (text) => {
    // معالجة الحالة التي يكون فيها النص null أو undefined
    if (!text || text === null || text === undefined) {
      return ''
    }
    
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    const inlineCodeRegex = /`([^`]+)`/g
    
    let formatted = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
    
    formatted = formatted.replace(codeBlockRegex, (match, lang, code) => {
      return `
        <div class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 my-2">
          <div class="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <span class="text-xs font-mono text-gray-500 dark:text-gray-400">${lang || 'code'}</span>
            <button class="text-xs text-gray-500 hover:text-primary transition-colors">نسخ الكود</button>
          </div>
          <div class="p-4 overflow-x-auto">
            <pre class="text-sm font-mono text-gray-800 dark:text-gray-300 leading-relaxed"><code>${code.trim()}</code></pre>
          </div>
        </div>
      `
    })
    
    formatted = formatted.replace(inlineCodeRegex, '<code class="font-mono text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">$1</code>')
    
    return formatted
  }

  if (message.type === 'user') {
    return (
      <div className="group flex gap-4 md:gap-6 py-6 border-b border-transparent hover:bg-gray-50/50 dark:hover:bg-gray-800/30 rounded-xl px-2 transition-colors flex-row-reverse message-enter">
        <div className="shrink-0 flex flex-col items-center">
          <div className="bg-primary rounded-full size-9 flex items-center justify-center text-white font-bold">
            U
          </div>
        </div>
        <div className="flex flex-col gap-2 w-full max-w-[80%] items-end">
          <div className="flex items-center gap-2 flex-row-reverse">
            <span className="text-sm font-semibold text-gray-900 dark:text-white">أنت</span>
            <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
          </div>
          <div className="bg-primary/10 dark:bg-primary/20 text-gray-900 dark:text-gray-100 px-5 py-3.5 rounded-2xl rounded-tr-sm text-base leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="group flex gap-4 md:gap-6 py-6 border-b border-transparent hover:bg-gray-50/50 dark:hover:bg-gray-800/30 rounded-xl px-2 transition-colors message-enter">
      <div className="shrink-0 flex flex-col items-center">
        <div className="bg-gradient-to-br from-primary to-blue-600 rounded-full size-9 flex items-center justify-center text-white font-bold">
          AI
        </div>
      </div>
      <div className="flex flex-col gap-3 w-full min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {message.type === 'error' ? 'خطأ' : 'موج'}
          </span>
          <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
        </div>
        <div 
          className="text-base leading-relaxed text-gray-800 dark:text-gray-200 font-normal space-y-4"
          dangerouslySetInnerHTML={{ __html: formatMessage(message.content) }}
        />
        {message.type !== 'error' && (
          <div className="flex items-center gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button 
              onClick={() => copyToClipboard(message.content)}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title="نسخ"
            >
              <FiCopy size={18} />
            </button>
            <button className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="إعادة توليد">
              <FiRefreshCw size={18} />
            </button>
            <button className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="إعجاب">
              <FiThumbsUp size={18} />
            </button>
            <button className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="عدم إعجاب">
              <FiThumbsDown size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default Message
