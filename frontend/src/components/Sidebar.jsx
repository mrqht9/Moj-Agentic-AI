import { useState, useEffect } from 'react'
import { MdDashboard, MdSettings, MdPerson, MdLogout } from 'react-icons/md'
import { BsListUl, BsFileText } from 'react-icons/bs'
import { FiSun, FiMoon, FiMessageSquare, FiUser, FiChevronUp, FiTrash2 } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import logoLight from '../assets/logos/logo-light.png'
import logoDark from '../assets/logos/logo-dark.png'

const Sidebar = ({ darkMode, setDarkMode, user, onLogout, onLoadConversation }) => {
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)

  const handleLogout = () => {
    if (window.confirm('هل أنت متأكد من تسجيل الخروج؟')) {
      onLogout()
      navigate('/login')
    }
  }

  useEffect(() => {
    if (user) {
      fetchConversations()
    }
  }, [user])

  const fetchConversations = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await axios.get(
        `${API_URL}/api/conversations/`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      if (response.data) {
        setConversations(response.data)
      }
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteConversation = async (conversationId, e) => {
    e.stopPropagation()
    
    if (!window.confirm('هل أنت متأكد من حذف هذه المحادثة؟')) {
      return
    }
    
    try {
      const token = localStorage.getItem('token')
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      await axios.delete(
        `${API_URL}/api/conversations/${conversationId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      )
      
      // تحديث القائمة بعد الحذف
      setConversations(conversations.filter(conv => conv.id !== conversationId))
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      alert('فشل حذف المحادثة')
    }
  }

  const handleLoadConversation = async (conversationId) => {
    if (onLoadConversation) {
      await onLoadConversation(conversationId)
    }
  }
  return (
    <aside className="hidden md:flex flex-col w-[260px] bg-sidebar-light dark:bg-sidebar-dark h-full shrink-0 transition-all duration-300">
      <div className="flex flex-col h-full p-4 gap-4">
        {/* فاصل خفيف في الأعلى */}
        <div className="border-b border-border-light dark:border-border-dark pb-4">
          <div className="flex justify-center px-3 pt-4">
            <img 
              src={darkMode ? logoLight : logoDark} 
              alt="MOJ AI Logo" 
              className="h-14 w-auto object-contain"
            />
          </div>
        </div>

        <button className="flex w-full items-center gap-3 px-4 py-3 rounded-xl bg-primary hover:bg-secondary transition-all duration-200 shadow-sm group">
          <MdDashboard className="text-white group-hover:scale-110 transition-transform" size={22} />
          <span className="text-sm font-semibold text-white">+ محادثة جديدة</span>
        </button>

        {/* قسم المحادثات السابقة */}
        <div className="flex flex-col gap-2 flex-1 overflow-hidden">
          <h3 className="text-xs font-semibold text-text-secondary-light dark:text-text-secondary-dark px-3 mt-2">
            المحادثات السابقة ({conversations.length})
          </h3>
          
          {loading ? (
            <div className="flex items-center justify-center py-4">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : conversations.length > 0 ? (
            <div className="flex-1 overflow-y-auto pr-2 space-y-1">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className="flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group"
                >
                  <button
                    onClick={() => handleLoadConversation(conversation.id)}
                    className="flex items-center gap-3 flex-1 min-w-0"
                  >
                    <FiMessageSquare className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-primary shrink-0" size={18} />
                    <div className="flex flex-col min-w-0 flex-1">
                      <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark truncate">
                        {conversation.title || 'محادثة بدون عنوان'}
                      </span>
                      <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark">
                        {new Date(conversation.updated_at).toLocaleDateString('ar-SA')}
                      </span>
                    </div>
                  </button>
                  <button
                    onClick={(e) => handleDeleteConversation(conversation.id, e)}
                    className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors opacity-0 group-hover:opacity-100"
                    title="حذف المحادثة"
                  >
                    <FiTrash2 className="text-red-500 dark:text-red-400" size={16} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-text-secondary-light dark:text-text-secondary-dark px-3 py-2">لا توجد محادثات سابقة</p>
          )}
        </div>

        <div className="mt-auto border-t border-border-light dark:border-border-dark pt-4 flex flex-col gap-1">
          <div className="relative">
            {showUserMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-card-light dark:bg-card-dark rounded-lg shadow-lg border border-border-light dark:border-border-dark overflow-hidden">
                {user?.is_admin && (
                  <button
                    onClick={() => {
                      setShowUserMenu(false)
                      navigate('/admin')
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-right border-b border-border-light dark:border-border-dark"
                  >
                    <MdDashboard className="text-purple-600 dark:text-purple-400" size={18} />
                    <span className="text-sm font-medium text-purple-600 dark:text-purple-400">لوحة التحكم الإدارية</span>
                  </button>
                )}
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    navigate('/profile')
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-right"
                >
                  <MdSettings className="text-text-secondary-light dark:text-text-secondary-dark" size={18} />
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">الإعدادات</span>
                </button>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-right"
                >
                  <MdPerson className="text-text-secondary-light dark:text-text-secondary-dark" size={18} />
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">كاتب المحتوى</span>
                </button>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    setDarkMode(!darkMode)
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-right"
                >
                  {darkMode ? (
                    <FiSun className="text-text-secondary-light dark:text-text-secondary-dark" size={18} />
                  ) : (
                    <FiMoon className="text-text-secondary-light dark:text-text-secondary-dark" size={18} />
                  )}
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">المظهر</span>
                </button>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    handleLogout()
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-right"
                >
                  <MdLogout className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-red-600 dark:group-hover:text-red-400" size={18} />
                  <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark group-hover:text-red-600 dark:group-hover:text-red-400">تسجيل الخروج</span>
                </button>
              </div>
            )}
            
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors cursor-pointer"
            >
              <div className="bg-primary rounded-full size-9 shrink-0 flex items-center justify-center text-white font-bold text-sm overflow-hidden">
                {user?.profile_picture ? (
                  <img src={user.profile_picture} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'
                )}
              </div>
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-sm font-semibold text-text-primary-light dark:text-text-primary-dark truncate">
                  {user?.name || user?.email || 'المستخدم'}
                </span>
                <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark truncate">Pro Plan</span>
              </div>
              <FiChevronUp 
                className={`text-text-secondary-light dark:text-text-secondary-dark transition-transform ${showUserMenu ? '' : 'rotate-180'}`} 
                size={16} 
              />
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
