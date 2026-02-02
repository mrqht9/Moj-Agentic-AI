import { useEffect, useRef, useState } from 'react'
import { FiSend, FiPlus, FiImage, FiFile } from 'react-icons/fi'

const MessageInput = ({ inputValue, setInputValue, handleSendMessage, isConnected, onAttachImage, onAttachFile, onFocusRef }) => {
  const [isAttachOpen, setIsAttachOpen] = useState(false)
  const imageInputRef = useRef(null)
  const fileInputRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    if (!onFocusRef) return
    onFocusRef.current = () => {
      textareaRef.current?.focus()
    }
  }, [onFocusRef])

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleChooseImage = () => {
    setIsAttachOpen(false)
    imageInputRef.current?.click()
  }

  const handleChooseFile = () => {
    setIsAttachOpen(false)
    fileInputRef.current?.click()
  }

  const handleImageSelected = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    await onAttachImage?.(file)
  }

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    await onAttachFile?.(file)
  }

  return (
    <div className="w-full bg-background-light dark:bg-background-dark pt-3 pb-4 px-4 md:px-8">
      <div className="w-full max-w-[840px] mx-auto">
        <div className="relative flex items-end w-full p-3 bg-card-light dark:bg-card-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm hover:shadow-md focus-within:border-primary dark:focus-within:border-primary transition-all duration-200">
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !isConnected}
            className={`p-2.5 mb-0.5 rounded-lg transition-all duration-200 shrink-0 ${
              inputValue.trim() && isConnected
                ? 'bg-primary hover:bg-secondary text-white'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
            }`}
          >
            <FiSend size={18} />
          </button>
          <div className="relative shrink-0 mb-0.5">
            <button
              type="button"
              onClick={() => setIsAttachOpen((v) => !v)}
              className="p-2 text-text-secondary-light dark:text-text-secondary-dark hover:text-primary dark:hover:text-primary transition-all duration-200 rounded-lg hover:bg-gray-50 dark:hover:bg-sidebar-dark"
              title="إرفاق"
            >
              <FiPlus size={20} />
            </button>

            {isAttachOpen && (
              <div className="absolute bottom-full mb-2 left-0 z-20 w-44 rounded-xl border border-border-light dark:border-border-dark bg-card-light dark:bg-card-dark shadow-lg overflow-hidden">
                <button
                  type="button"
                  onClick={handleChooseImage}
                  className="w-full flex items-center gap-2 px-4 py-3 text-right hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <FiImage size={18} className="text-text-secondary-light dark:text-text-secondary-dark" />
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">إرفاق صورة</span>
                </button>
                <button
                  type="button"
                  onClick={handleChooseFile}
                  className="w-full flex items-center gap-2 px-4 py-3 text-right hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-t border-border-light dark:border-border-dark"
                >
                  <FiFile size={18} className="text-text-secondary-light dark:text-text-secondary-dark" />
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">إرفاق ملف</span>
                </button>
              </div>
            )}

            <input
              ref={imageInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleImageSelected}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf,application/msword,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,application/vnd.ms-excel,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.xlsx"
              className="hidden"
              onChange={handleFileSelected}
            />
          </div>
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full max-h-[200px] py-3 px-3 bg-transparent border-0 focus:ring-0 text-text-primary-light dark:text-text-primary-dark placeholder-text-secondary-light dark:placeholder-text-secondary-dark resize-none leading-relaxed outline-none text-sm"
            placeholder="اكتب رسالتك بالتفصيل..."
            rows="1"
            style={{ minHeight: '48px' }}
          />
        </div>
        <div className="text-center mt-2">
          <p className="text-xs text-text-secondary-light dark:text-text-secondary-dark">
            Mwj AI يمكن أن يخطئ. تحقق من المعلومات المهمة.
          </p>
        </div>
      </div>
    </div>
  )
}

export default MessageInput
