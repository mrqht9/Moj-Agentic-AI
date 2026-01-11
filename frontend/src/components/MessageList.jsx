import Message from './Message'
import TypingIndicator from './TypingIndicator'

const MessageList = ({ messages, isTyping, messagesEndRef }) => {
  return (
    <div className="flex-1 overflow-y-auto w-full">
      <div className="flex flex-col w-full max-w-[840px] mx-auto px-4 py-6 md:px-8 pb-32">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

export default MessageList
