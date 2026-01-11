import Message from './Message'
import TypingIndicator from './TypingIndicator'

const MessageList = ({ messages, isTyping, messagesEndRef }) => {
  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 pb-2">
      <div className="flex flex-col w-full max-w-[900px] mx-auto">
        <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl border-2 border-gray-200 dark:border-gray-700 p-6 md:p-8 min-h-[200px]">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="bg-gradient-to-br from-primary to-blue-600 rounded-full size-20 flex items-center justify-center text-white font-bold shadow-lg mb-6 animate-gradient">
                <span className="text-3xl">🤖</span>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">مرحباً بك في MOJ AI</h3>
              <p className="text-gray-600 dark:text-gray-400 max-w-md">
                أنا مساعدك الذكي لإدارة وسائل التواصل الاجتماعي. كيف يمكنني مساعدتك اليوم؟
              </p>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <Message key={message.id} message={message} />
              ))}
              {isTyping && <TypingIndicator />}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </div>
  )
}

export default MessageList
