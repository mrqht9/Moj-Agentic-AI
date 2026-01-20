import { MdDashboard, MdSettings, MdPerson, MdLogout } from 'react-icons/md'
import { BsListUl, BsFileText } from 'react-icons/bs'
import { FiSun, FiMoon, FiMessageSquare } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import logoLight from '../assets/logos/logo-light.png'
import logoDark from '../assets/logos/logo-dark.png'

const Sidebar = ({ darkMode, setDarkMode, user, onLogout }) => {
  const navigate = useNavigate()

  const handleLogout = () => {
    if (window.confirm('هل أنت متأكد من تسجيل الخروج؟')) {
      onLogout()
      navigate('/login')
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
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold text-text-secondary-light dark:text-text-secondary-dark px-3 mt-2">المحادثات</h3>
          
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <FiMessageSquare className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark truncate">خطة محتوى الأسبوع</span>
          </button>
          
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <FiMessageSquare className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark truncate">تحليل المنافسين</span>
          </button>
          
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <FiMessageSquare className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark truncate">استراتيجية إطلاق المنتج</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-2"></div>

        <div className="mt-auto border-t border-border-light dark:border-border-dark pt-4 flex flex-col gap-1">
          <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <MdSettings className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark">الإعدادات</span>
          </button>
          <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <MdPerson className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark">كاتب المحتوى</span>
          </button>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group cursor-pointer"
          >
            {darkMode ? (
              <FiSun className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            ) : (
              <FiMoon className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            )}
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark">المظهر</span>
          </button>

          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-right group"
          >
            <MdLogout className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-red-600 dark:group-hover:text-red-400" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-red-600 dark:group-hover:text-red-400">تسجيل الخروج</span>
          </button>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors cursor-pointer mt-2">
            <div className="bg-primary rounded-full size-9 shrink-0 flex items-center justify-center text-white font-bold text-sm">
              {user?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold text-text-primary-light dark:text-text-primary-dark truncate">{user?.name || 'المستخدم'}</span>
              <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark truncate">Pro Plan</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
