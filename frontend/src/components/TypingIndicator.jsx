const TypingIndicator = () => {
  return (
    <div className="group flex gap-4 md:gap-6 py-6 border-b border-transparent rounded-xl px-2 message-enter">
      <div className="shrink-0 flex flex-col items-center">
        <div className="bg-gradient-to-br from-primary to-blue-600 rounded-full size-9 flex items-center justify-center text-white font-bold">
          AI
        </div>
      </div>
      <div className="flex flex-col gap-2 w-full min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">موج</span>
        </div>
        <div className="flex gap-1 py-2">
          <span className="w-2 h-2 bg-primary rounded-full typing-dot"></span>
          <span className="w-2 h-2 bg-primary rounded-full typing-dot"></span>
          <span className="w-2 h-2 bg-primary rounded-full typing-dot"></span>
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator
