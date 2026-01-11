import { FiSend, FiPlus } from 'react-icons/fi'

const MessageInput = ({ inputValue, setInputValue, handleSendMessage, isConnected }) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="w-full bg-gradient-to-t from-white via-white dark:from-background-dark dark:via-background-dark to-transparent pt-3 pb-4 px-4 md:px-8">
      <div className="w-full max-w-[840px] mx-auto">
        <div className="relative flex items-end w-full p-4 bg-white dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-3xl shadow-lg hover:shadow-xl focus-within:shadow-2xl focus-within:border-primary dark:focus-within:border-primary transition-all duration-300">
          <button className="p-2.5 text-gray-400 hover:text-primary dark:text-gray-500 dark:hover:text-primary transition-all duration-200 rounded-xl hover:bg-primary/10 dark:hover:bg-primary/20 shrink-0 mb-0.5 hover:scale-110">
            <FiPlus size={22} />
          </button>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full max-h-[200px] py-3 px-4 bg-transparent border-0 focus:ring-0 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 resize-none leading-relaxed outline-none text-base"
            placeholder="اكتب رسالتك هنا... (اضغط Enter للإرسال)"
            rows="1"
            style={{ minHeight: '48px' }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !isConnected}
            className={`p-3 mb-0.5 rounded-xl transition-all duration-300 shrink-0 shadow-md ${
              inputValue.trim() && isConnected
                ? 'bg-gradient-to-r from-primary to-blue-600 hover:from-blue-600 hover:to-primary text-white hover:shadow-lg hover:scale-105 active:scale-95'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            <FiSend size={20} className={inputValue.trim() && isConnected ? 'animate-pulse' : ''} />
          </button>
        </div>
        <div className="text-center mt-3">
          <p className="text-xs text-gray-400 dark:text-gray-500 font-medium">
            💬 MOJ AI - مدعوم بالذكاء الاصطناعي المتقدم
          </p>
        </div>
      </div>
    </div>
  )
}

export default MessageInput
