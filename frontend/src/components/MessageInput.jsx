import { FiSend, FiPlus } from 'react-icons/fi'

const MessageInput = ({ inputValue, setInputValue, handleSendMessage, isConnected }) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="absolute bottom-0 w-full bg-white dark:bg-background-dark pt-2 pb-6 px-4 md:px-8">
      <div className="w-full max-w-[840px] mx-auto">
        <div className="relative flex items-end w-full p-3 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
          <button className="p-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 shrink-0 mb-0.5">
            <FiPlus size={24} />
          </button>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full max-h-[200px] py-3 px-3 bg-transparent border-0 focus:ring-0 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 resize-none leading-relaxed outline-none"
            placeholder="اكتب رسالتك هنا..."
            rows="1"
            style={{ minHeight: '48px' }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !isConnected}
            className={`p-2 mb-0.5 rounded-lg transition-colors shrink-0 shadow-sm ${
              inputValue.trim() && isConnected
                ? 'bg-primary hover:bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            <FiSend size={20} />
          </button>
        </div>
        <div className="text-center mt-2">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            موج AI - نظام إدارة وسائل التواصل الاجتماعي بالذكاء الاصطناعي
          </p>
        </div>
      </div>
      <div className="absolute top-[-40px] left-0 w-full h-10 bg-gradient-to-t from-white dark:from-background-dark to-transparent pointer-events-none"></div>
    </div>
  )
}

export default MessageInput
