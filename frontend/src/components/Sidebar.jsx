import { MdDashboard, MdSettings, MdPerson, MdLogout } from 'react-icons/md'
import { BsListUl, BsFileText } from 'react-icons/bs'
import { FiSun, FiMoon } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import logoLight from '../assets/logos/logo-light.svg'
import logoDark from '../assets/logos/logo-dark.svg'

const Sidebar = ({ darkMode, setDarkMode, user, onLogout }) => {
  const navigate = useNavigate()

  const handleLogout = () => {
    if (window.confirm('هل أنت متأكد من تسجيل الخروج؟')) {
      onLogout()
      navigate('/login')
    }
  }
  return (
    <aside className="hidden md:flex flex-col w-[260px] bg-sidebar-light dark:bg-sidebar-dark border-r border-border-light dark:border-border-dark h-full shrink-0 transition-all duration-300">
      <div className="flex flex-col h-full p-4 gap-4">
        <div className="px-3 pt-2">
          <img 
            src={darkMode ? logoDark : logoLight} 
            alt="MOJ AI Logo" 
            className="h-10 w-auto object-contain"
          />
        </div>

        <button className="flex w-full items-center gap-3 px-4 py-3 rounded-xl bg-primary hover:bg-secondary transition-all duration-200 shadow-sm group mt-2">
          <MdDashboard className="text-white group-hover:scale-110 transition-transform" size={22} />
          <span className="text-sm font-semibold text-white">+ محادثة جديدة</span>
        </button>

        <div className="flex flex-col flex-1 gap-2 overflow-y-auto pr-2 mt-2">
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <BsListUl className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark">عمليات الحسابات</span>
          </button>
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors text-right group">
            <BsFileText className="text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark" size={18} />
            <span className="text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark group-hover:text-text-primary-light dark:group-hover:text-text-primary-dark">استوديو الهوية</span>
          </button>
        </div>

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
