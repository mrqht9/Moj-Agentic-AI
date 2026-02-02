import Message from './Message'
import TypingIndicator from './TypingIndicator'

const MessageList = ({ messages, isTyping, messagesEndRef, showSuggestions, onSuggestionClick }) => {
  const suggestions = [
    'أضف حساب تويتر',
    'إدارة المحتوى',
    'إدارة الحسابات',
    'انشاء هوية',
    'تفعيل الحساب'
  ]

  const hasUserMessage = messages.some((m) => m?.type === 'user')
  const shouldShowSuggestions = !!showSuggestions && !hasUserMessage && messages.length > 0

  return (
    <div className="flex-1 overflow-y-auto w-full p-4 md:p-6 pb-2">
      <div className="flex flex-col w-full max-w-[900px] mx-auto">
        <div className="bg-card-light dark:bg-card-dark rounded-2xl shadow-sm border border-border-light dark:border-border-dark p-6 md:p-8 min-h-[200px]">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="bg-primary rounded-full size-16 flex items-center justify-center text-white font-bold shadow-md mb-6">
                <span className="text-3xl">🤖</span>
              </div>
              <h3 className="text-2xl font-bold text-text-primary-light dark:text-text-primary-dark mb-3">مرحباً بك في Mwj AI</h3>
              <p className="text-text-secondary-light dark:text-text-secondary-dark max-w-md">
                أنا مساعدك الذكي لإدارة وسائل التواصل الاجتماعي. كيف يمكنني مساعدتك اليوم؟
              </p>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <Message key={message.id} message={message} />
              ))}

              {shouldShowSuggestions && (
                <div className="mt-4 mb-2">
                  <div className="text-xs font-semibold text-text-secondary-light dark:text-text-secondary-dark mb-2 text-right">
                    اقتراحات سريعة
                  </div>
                  <div className="flex flex-wrap gap-2 justify-start">
                    {suggestions.map((text) => (
                      <button
                        key={text}
                        type="button"
                        onClick={() => onSuggestionClick?.(text)}
                        className="relative overflow-hidden px-4 py-2 rounded-full text-sm font-semibold border border-white/35 dark:border-white/10 bg-white/30 dark:bg-white/5 backdrop-blur-xl shadow-[0_10px_30px_rgba(0,0,0,0.08)] dark:shadow-[0_14px_40px_rgba(0,0,0,0.45)] ring-1 ring-white/20 dark:ring-white/10 hover:ring-white/35 dark:hover:ring-white/20 hover:bg-white/45 dark:hover:bg-white/10 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 text-text-primary-light dark:text-text-primary-dark before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white/35 before:to-transparent before:-translate-x-full hover:before:translate-x-full before:transition-transform before:duration-700 before:ease-out"
                      >
                        {text}
                      </button>
                    ))}
                  </div>
                </div>
              )}

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
