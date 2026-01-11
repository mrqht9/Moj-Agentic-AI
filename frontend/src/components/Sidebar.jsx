import { MdDashboard, MdSettings, MdPerson, MdLogout } from 'react-icons/md'
import { BsListUl, BsFileText } from 'react-icons/bs'
import { FiSun, FiMoon } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'

const Sidebar = ({ darkMode, setDarkMode, user, onLogout }) => {
  const navigate = useNavigate()

  const handleLogout = () => {
    if (window.confirm('هل أنت متأكد من تسجيل الخروج؟')) {
      onLogout()
      navigate('/login')
    }
  }
  return (
    <aside className="hidden md:flex flex-col w-[260px] bg-sidebar-light dark:bg-sidebar-dark border-r border-gray-200 dark:border-gray-800 h-full shrink-0 transition-all duration-300">
      <div className="flex flex-col h-full p-4 gap-4">
        <div className="px-3 pt-2">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">MOJ AI</h1>
        </div>

        <button className="flex w-full items-center gap-3 px-3 py-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-800 transition-colors shadow-sm bg-white dark:bg-transparent group mt-2">
          <MdDashboard className="text-primary group-hover:scale-110 transition-transform" size={24} />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">لوحة التحكم</span>
        </button>

        <div className="flex flex-col flex-1 gap-2 overflow-y-auto pr-2 mt-2">
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left group">
            <BsListUl className="text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-200" size={20} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">تفاصيل العمليات</span>
          </button>
          <button className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left group">
            <BsFileText className="text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-200" size={20} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">ملخص</span>
          </button>
        </div>

        <div className="mt-auto border-t border-gray-200 dark:border-gray-800 pt-4 flex flex-col gap-1">
          <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left group">
            <MdSettings className="text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-200" size={20} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">الإعدادات</span>
          </button>
          <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left group">
            <MdPerson className="text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-200" size={20} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">البروفايل</span>
          </button>
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left group cursor-pointer"
          >
            {darkMode ? (
              <FiSun className="text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-200" size={20} />
            ) : (
              <FiMoon className="text-gray-500 group-hover:text-gray-700 dark:group-hover:text-gray-200" size={20} />
            )}
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">المظهر</span>
          </button>

          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-left group"
          >
            <MdLogout className="text-gray-500 group-hover:text-red-600 dark:group-hover:text-red-400" size={20} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-red-600 dark:group-hover:text-red-400">تسجيل الخروج</span>
          </button>

          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer mt-2">
            <div className="bg-primary rounded-full size-8 shrink-0 flex items-center justify-center text-white font-bold">
              {user?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-bold text-gray-900 dark:text-white truncate">{user?.name || 'المستخدم'}</span>
              <span className="text-xs text-gray-500 truncate">Pro Plan</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
