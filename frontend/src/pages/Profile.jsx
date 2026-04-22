import { useEffect, useState } from 'react'
import axios from 'axios'
import { FiCamera, FiUser, FiMail, FiLock, FiCheck } from 'react-icons/fi'
import { MdClose } from 'react-icons/md'

const EMPTY_TELEGRAM_DATA = {
  bot_token: '',
  chat_id: '',
  webhook_base_url: ''
}

const TELEGRAM_BOT_TOKEN_PATTERN = /^\d+:[A-Za-z0-9_-]{10,}$/

const normalizeTelegramBotToken = (value) => {
  const match = value.match(/\d+:[A-Za-z0-9_-]{10,}/)
  return match ? match[0] : value.trim()
}

const Profile = ({ user, setUser, darkMode }) => {
  const [loading, setLoading] = useState(false)
  const [telegramLoading, setTelegramLoading] = useState(false)
  const [message, setMessage] = useState({ text: '', type: '' })

  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    email: user?.email || ''
  })

  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  const [profilePicture, setProfilePicture] = useState(user?.profile_picture || '')
  const [previewImage, setPreviewImage] = useState(user?.profile_picture || '')
  const [telegramData, setTelegramData] = useState(EMPTY_TELEGRAM_DATA)
  const [telegramIntegration, setTelegramIntegration] = useState(null)

  useEffect(() => {
    if (user) {
      setProfileData({
        name: user.name || '',
        email: user.email || ''
      })
      setProfilePicture(user.profile_picture || '')
      setPreviewImage(user.profile_picture || '')
    }
  }, [user])

  useEffect(() => {
    const fetchTelegramStatus = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        return
      }

      try {
        const response = await axios.get('/api/telegram/status', {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
        setTelegramIntegration(response.data.integration || null)
      } catch (error) {
        setTelegramIntegration(null)
      }
    }

    fetchTelegramStatus()
  }, [])

  const showMessage = (text, type) => {
    setMessage({ text, type })
    setTimeout(() => setMessage({ text: '', type: '' }), 5000)
  }

  const handleImageChange = (e) => {
    const file = e.target.files[0]
    if (!file) {
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      showMessage('حجم الصورة يجب أن يكون أقل من 5 ميجابايت', 'error')
      return
    }

    const reader = new FileReader()
    reader.onloadend = () => {
      setPreviewImage(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const handleUploadProfilePicture = async () => {
    if (!previewImage || previewImage === profilePicture) {
      showMessage('الرجاء اختيار صورة جديدة', 'error')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(
        '/api/auth/profile-picture',
        { profile_picture: previewImage },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      const newProfilePicture = response.data.profile_picture
      const updatedUser = { ...user, profile_picture: newProfilePicture }

      setProfilePicture(newProfilePicture)
      setPreviewImage(newProfilePicture)
      setUser(updatedUser)
      localStorage.setItem('user', JSON.stringify(updatedUser))

      showMessage('تم تحديث الصورة الشخصية بنجاح', 'success')
    } catch (error) {
      showMessage(error.response?.data?.detail || 'فشل تحديث الصورة', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateProfile = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const token = localStorage.getItem('token')
      const response = await axios.put('/api/auth/profile', profileData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      const updatedUser = { ...user, ...response.data }
      setUser(updatedUser)
      localStorage.setItem('user', JSON.stringify(updatedUser))
      showMessage('تم تحديث البروفايل بنجاح', 'success')
    } catch (error) {
      showMessage(error.response?.data?.detail || 'فشل تحديث البروفايل', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()

    if (!passwordData.current_password) {
      showMessage('الرجاء إدخال كلمة المرور الحالية', 'error')
      return
    }

    if (!passwordData.new_password) {
      showMessage('الرجاء إدخال كلمة المرور الجديدة', 'error')
      return
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      showMessage('كلمة المرور الجديدة غير متطابقة', 'error')
      return
    }

    if (passwordData.new_password.length < 6) {
      showMessage('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      await axios.post(
        '/api/auth/change-password',
        {
          current_password: passwordData.current_password,
          new_password: passwordData.new_password
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      })
      showMessage('تم تغيير كلمة المرور بنجاح', 'success')
    } catch (error) {
      showMessage(error.response?.data?.detail || 'فشل تغيير كلمة المرور', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleTelegramFieldChange = (field, value) => {
    const nextValue = field === 'bot_token'
      ? normalizeTelegramBotToken(value)
      : value

    setTelegramData((prev) => ({
      ...prev,
      [field]: nextValue
    }))
  }

  const handleConnectTelegram = async (e) => {
    e.preventDefault()

    const botToken = normalizeTelegramBotToken(telegramData.bot_token)
    const chatId = telegramData.chat_id.trim()
    const webhookBaseUrl = telegramData.webhook_base_url.trim().replace(/\/+$/, '')

    if (!botToken) {
      showMessage('الرجاء إدخال Telegram Bot Token', 'error')
      return
    }

    if (!TELEGRAM_BOT_TOKEN_PATTERN.test(botToken)) {
      showMessage('Bot Token غير صالح. الصق توكن BotFather الحقيقي فقط', 'error')
      return
    }

    if (!chatId) {
      showMessage('الرجاء إدخال Telegram Chat ID', 'error')
      return
    }

    if (!webhookBaseUrl) {
      showMessage('الرجاء إدخال Public Base URL', 'error')
      return
    }

    setTelegramLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(
        '/api/telegram/connect',
        {
          bot_token: botToken,
          chat_id: chatId,
          webhook_base_url: webhookBaseUrl
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      setTelegramIntegration(response.data.integration)
      setTelegramData(EMPTY_TELEGRAM_DATA)
      showMessage('تم ربط Telegram بنجاح', 'success')
    } catch (error) {
      console.error('Telegram connect failed:', error.response?.data || error.message)
      showMessage(error.response?.data?.detail || 'فشل ربط Telegram', 'error')
    } finally {
      setTelegramLoading(false)
    }
  }

  const handleToggleTelegram = async (isEnabled) => {
    setTelegramLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(
        '/api/telegram/toggle',
        { is_enabled: isEnabled },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      setTelegramIntegration(response.data.integration)
      showMessage(isEnabled ? 'تم تفعيل Telegram' : 'تم إيقاف Telegram', 'success')
    } catch (error) {
      showMessage(error.response?.data?.detail || 'فشل تحديث حالة Telegram', 'error')
    } finally {
      setTelegramLoading(false)
    }
  }

  const handleDisconnectTelegram = async () => {
    setTelegramLoading(true)
    try {
      const token = localStorage.getItem('token')
      await axios.delete('/api/telegram', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      setTelegramIntegration(null)
      setTelegramData(EMPTY_TELEGRAM_DATA)
      showMessage('تم فصل Telegram بنجاح', 'success')
    } catch (error) {
      showMessage(error.response?.data?.detail || 'فشل فصل Telegram', 'error')
    } finally {
      setTelegramLoading(false)
    }
  }

  return (
    <div className="w-full bg-background-light dark:bg-background-dark">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-text-primary-light dark:text-text-primary-dark">
            إعدادات الحساب
          </h1>
        </div>

        {message.text && (
          <div className={`mb-6 p-4 rounded-lg flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
              : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
          }`}>
            <div className="flex items-center gap-2">
              {message.type === 'success' ? <FiCheck size={20} /> : <MdClose size={20} />}
              <span>{message.text}</span>
            </div>
            <button onClick={() => setMessage({ text: '', type: '' })}>
              <MdClose size={20} />
            </button>
          </div>
        )}

        <div className="space-y-6">
          <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary-light dark:text-text-primary-dark mb-6">
              الصورة الشخصية
            </h2>

            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="relative">
                <div className="w-32 h-32 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  {previewImage ? (
                    <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <FiUser size={48} className="text-gray-400" />
                  )}
                </div>
                <label className="absolute bottom-0 right-0 bg-primary hover:bg-secondary text-white p-2 rounded-full cursor-pointer shadow-lg transition-colors">
                  <FiCamera size={20} />
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                  />
                </label>
              </div>

              <div className="flex-1 text-center md:text-right">
                <p className="text-text-secondary-light dark:text-text-secondary-dark mb-4">
                  اختر صورة بصيغة JPG أو PNG. الحد الأقصى للحجم 5 ميجابايت.
                </p>
                <button
                  onClick={handleUploadProfilePicture}
                  disabled={loading || !previewImage || previewImage === profilePicture}
                  className="px-6 py-2 bg-primary hover:bg-secondary text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'جاري الرفع...' : 'حفظ الصورة'}
                </button>
              </div>
            </div>
          </div>

          <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary-light dark:text-text-primary-dark mb-6">
              المعلومات الشخصية
            </h2>

            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  الاسم
                </label>
                <div className="relative">
                  <FiUser className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary-light dark:text-text-secondary-dark" />
                  <input
                    type="text"
                    value={profileData.name}
                    onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                    className="w-full pr-10 pl-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="أدخل اسمك"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  البريد الإلكتروني
                </label>
                <div className="relative">
                  <FiMail className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary-light dark:text-text-secondary-dark" />
                  <input
                    type="email"
                    value={profileData.email}
                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                    className="w-full pr-10 pl-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="example@email.com"
                    dir="ltr"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-primary hover:bg-secondary text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'جاري الحفظ...' : 'حفظ التغييرات'}
              </button>
            </form>
          </div>

          <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary-light dark:text-text-primary-dark mb-6">
              تغيير كلمة المرور
            </h2>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  كلمة المرور الحالية
                </label>
                <div className="relative">
                  <FiLock className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary-light dark:text-text-secondary-dark" />
                  <input
                    type="password"
                    value={passwordData.current_password}
                    onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
                    className="w-full pr-10 pl-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="أدخل كلمة المرور الحالية"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  كلمة المرور الجديدة
                </label>
                <div className="relative">
                  <FiLock className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary-light dark:text-text-secondary-dark" />
                  <input
                    type="password"
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                    className="w-full pr-10 pl-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="أدخل كلمة المرور الجديدة"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  تأكيد كلمة المرور الجديدة
                </label>
                <div className="relative">
                  <FiLock className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-secondary-light dark:text-text-secondary-dark" />
                  <input
                    type="password"
                    value={passwordData.confirm_password}
                    onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                    className="w-full pr-10 pl-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="أعد إدخال كلمة المرور الجديدة"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-primary hover:bg-secondary text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'جاري التغيير...' : 'تغيير كلمة المرور'}
              </button>
            </form>
          </div>

          <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary-light dark:text-text-primary-dark mb-2">
              تكامل Telegram
            </h2>
            <p className="text-sm text-text-secondary-light dark:text-text-secondary-dark mb-6">
              اربط بوت Telegram الخاص بك مع موج حتى تستقبل وترسل الرسائل من خلال تيليجرام.
            </p>

            {telegramIntegration && (
              <div className="mb-6 p-4 rounded-lg bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark space-y-2">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <span className="text-text-primary-light dark:text-text-primary-dark font-medium">
                    الحالة: {telegramIntegration.is_enabled ? 'مفعّل' : 'متوقف'}
                  </span>
                  <span className="text-sm text-text-secondary-light dark:text-text-secondary-dark">
                    Chat ID: {telegramIntegration.chat_id}
                  </span>
                </div>
                {telegramIntegration.bot_username && (
                  <div className="text-sm text-text-secondary-light dark:text-text-secondary-dark">
                    البوت: @{telegramIntegration.bot_username}
                  </div>
                )}
                {telegramIntegration.webhook_url && (
                  <div className="text-xs break-all text-text-secondary-light dark:text-text-secondary-dark" dir="ltr">
                    Webhook: {telegramIntegration.webhook_url}
                  </div>
                )}
                {telegramIntegration.last_error && (
                  <div className="text-sm text-red-600 dark:text-red-400">
                    آخر خطأ: {telegramIntegration.last_error}
                  </div>
                )}
              </div>
            )}

            <form onSubmit={handleConnectTelegram} className="space-y-4" autoComplete="off">
              <input
                type="text"
                name="telegram_fake_username"
                autoComplete="username"
                tabIndex={-1}
                className="hidden"
                aria-hidden="true"
              />
              <input
                type="password"
                name="telegram_fake_password"
                autoComplete="new-password"
                tabIndex={-1}
                className="hidden"
                aria-hidden="true"
              />

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  Bot Token
                </label>
                <input
                  type="text"
                  name="telegram_bot_token_input"
                  value={telegramData.bot_token}
                  onChange={(e) => handleTelegramFieldChange('bot_token', e.target.value)}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  data-lpignore="true"
                  data-1p-ignore="true"
                  dir="ltr"
                  className="w-full px-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="123456789:AA..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  Chat ID
                </label>
                <input
                  type="text"
                  name="telegram_chat_id_input"
                  value={telegramData.chat_id}
                  onChange={(e) => handleTelegramFieldChange('chat_id', e.target.value)}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  data-lpignore="true"
                  data-1p-ignore="true"
                  dir="ltr"
                  className="w-full px-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="مثال: 123456789"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary-light dark:text-text-secondary-dark mb-2">
                  Public Base URL
                </label>
                <input
                  type="text"
                  name="telegram_webhook_base_url_input"
                  value={telegramData.webhook_base_url}
                  onChange={(e) => handleTelegramFieldChange('webhook_base_url', e.target.value)}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck={false}
                  data-lpignore="true"
                  data-1p-ignore="true"
                  dir="ltr"
                  className="w-full px-4 py-3 bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark rounded-lg text-text-primary-light dark:text-text-primary-dark focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="https://your-domain.com"
                />
                <p className="mt-2 text-xs text-text-secondary-light dark:text-text-secondary-dark">
                  إذا كان المشروع محليًا، ضع رابطًا عامًا مثل ngrok لأن Telegram لا يستطيع الوصول إلى localhost.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={telegramLoading}
                  className="px-5 py-3 bg-primary hover:bg-secondary text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {telegramLoading ? 'جاري الربط...' : telegramIntegration ? 'تحديث الربط' : 'ربط Telegram'}
                </button>

                {telegramIntegration && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleToggleTelegram(!telegramIntegration.is_enabled)}
                      disabled={telegramLoading}
                      className="px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {telegramIntegration.is_enabled ? 'إيقاف التكامل' : 'تفعيل التكامل'}
                    </button>

                    <button
                      type="button"
                      onClick={handleDisconnectTelegram}
                      disabled={telegramLoading}
                      className="px-5 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      فصل Telegram
                    </button>
                  </>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Profile
