import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Logo } from '../components/Logo'
import { Button } from '../components/ui/button'
import { ServiceCard } from '../components/ServiceCard'
import { TrustBadge } from '../components/TrustBadge'
import { ThemeToggle } from '../components/ThemeToggle'
import {
  Link2,
  User,
  Target,
  Palette,
  Calendar,
  Users,
  Megaphone,
  BarChart3,
  Shield,
  Scale,
  CheckCircle2,
  Play,
  ArrowLeft,
  ChevronDown,
} from 'lucide-react'

const LandingPage = ({ darkMode, setDarkMode, user, onLogout }) => {
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [lastPointerPos, setLastPointerPos] = useState(null)

  const createRipple = (x, y) => {
    const viewX = typeof x === 'number' ? x : window.innerWidth / 2
    const viewY = typeof y === 'number' ? y : window.innerHeight / 2

    for (let i = 0; i < 4; i++) {
      const circle = document.createElement('span')
      circle.className = 'mwj-ripple__circle mwj-ripple__circle--global'
      circle.style.left = `${viewX}px`
      circle.style.top = `${viewY}px`
      circle.style.animationDelay = `${i * 220}ms`
      circle.style.setProperty('--mwj-ripple-alpha', `${0.30 - i * 0.05}`)
      circle.style.setProperty('--mwj-ripple-scale', `${38 + i * 6}`)
      circle.style.setProperty('--mwj-ripple-blur', `${10 + i * 2}px`)
      circle.addEventListener('animationend', () => {
        circle.remove()
      })
      document.body.appendChild(circle)
    }
  }

  const handleStartNowPointerDown = (e) => {
    const x = e.clientX
    const y = e.clientY
    setLastPointerPos({ x, y })
    createRipple(x, y)
  }

  const handleStartNowClick = (e) => {
    const button = e.currentTarget

    // In case of keyboard activation (no pointerdown), create ripple from center.
    if (!lastPointerPos) {
      const rect = button.getBoundingClientRect()
      createRipple(rect.left + rect.width / 2, rect.top + rect.height / 2)
    }

    // Delay navigation so ripple is visible.
    window.setTimeout(() => {
      navigate('/login')
    }, 820)
    setLastPointerPos(null)
  }

  useEffect(() => {
    const handler = (e) => {
      const target = e.target
      if (!(target instanceof Element)) return
      if (target.closest('[data-mwj-user-menu]')) return
      setShowUserMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const services = useMemo(
    () => [
      { icon: Link2, title: 'ربط المنصات', description: 'اربط حساباتك بنقرة' },
      { icon: User, title: 'هوية الحساب', description: 'بناء هوية متماسكة' },
      { icon: Target, title: 'الاستراتيجية', description: 'خطط ذكية للنمو' },
      { icon: Palette, title: 'استوديو المحتوى', description: 'إنشاء محتوى مميز' },
      { icon: Calendar, title: 'الجدولة', description: 'نشر تلقائي دقيق' },
      { icon: Users, title: 'المجتمع', description: 'تفاعل مع جمهورك' },
      { icon: Megaphone, title: 'الإعلانات', description: 'حملات فعّالة' },
      { icon: BarChart3, title: 'التحليلات', description: 'قرارات مبنية على بيانات' },
    ],
    [],
  )

  const trustItems = useMemo(
    () => [
      { icon: Shield, label: 'أمان' },
      { icon: Scale, label: 'حوكمة' },
      { icon: CheckCircle2, label: 'بوابة جودة' },
    ],
    [],
  )

  return (
    <div className="min-h-screen bg-background-light text-text-primary-light dark:bg-background-dark dark:text-text-primary-dark">
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-border-light/50 bg-background-light/80 backdrop-blur-md dark:border-border-dark/50 dark:bg-background-dark/80">
        <div className="container mx-auto flex items-center justify-between px-4 py-3 sm:px-6 sm:py-4">
          <Logo size="md" className="shrink-0" />

          <div className="flex items-center gap-1 sm:gap-2">
            <ThemeToggle darkMode={darkMode} setDarkMode={setDarkMode} />

            {user ? (
              <div className="relative" data-mwj-user-menu>
                {showUserMenu && (
                  <div className="absolute top-full left-0 mt-2 w-56 bg-card-light dark:bg-card-dark rounded-lg shadow-lg border border-border-light dark:border-border-dark overflow-hidden">
                    <button
                      onClick={() => {
                        setShowUserMenu(false)
                        navigate('/profile')
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-right"
                    >
                      <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">الإعدادات</span>
                      <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark">↗</span>
                    </button>
                    <button
                      onClick={() => {
                        setShowUserMenu(false)
                        if (window.confirm('هل أنت متأكد من تسجيل الخروج؟')) {
                          onLogout?.()
                          navigate('/login')
                        }
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-right border-t border-border-light dark:border-border-dark"
                    >
                      <span className="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">تسجيل الخروج</span>
                      <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark">⎋</span>
                    </button>
                  </div>
                )}

                <button
                  onClick={() => setShowUserMenu((v) => !v)}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-card-dark transition-colors cursor-pointer"
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
                      {user?.name || user?.email}
                    </span>
                    <span className="text-xs text-text-secondary-light dark:text-text-secondary-dark truncate">Pro Plan</span>
                  </div>
                  <ChevronDown className="text-text-secondary-light dark:text-text-secondary-dark transition-transform" size={16} />
                </button>
              </div>
            ) : (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="hidden sm:inline-flex"
                  onClick={() => navigate('/login')}
                >
                  تسجيل الدخول
                </Button>
                <Button variant="default" size="sm" onClick={() => navigate('/register')}>
                  إنشاء حساب
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="mwj-gradient-subtle relative overflow-hidden pt-24 pb-12 sm:pt-32 sm:pb-20">
        <div className="container mx-auto max-w-4xl px-4 text-center sm:px-6">
          <div className="animate-fade-in">
            <h1 className="mb-4 text-3xl font-bold leading-tight sm:mb-6 sm:text-4xl md:text-5xl lg:text-6xl">
موج لإدارة مواقع التواصل
              <span className="mwj-gradient-text block mt-2"> </span>
            </h1>
            <p className="mx-auto mb-8 max-w-2xl px-2 text-base leading-relaxed text-text-secondary-light dark:text-text-secondary-dark sm:mb-10 sm:text-lg md:text-xl">
              منصة متكاملة بوكلاء ذكاء الإصطناعي تدير حساباتك من الإنشاء الى التفاعل
            </p>
          </div>

          <div className="animate-fade-in" style={{ animationDelay: '200ms' }}>
            <div className="flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Button size="lg" className="w-full sm:w-auto mwj-ripple" variant="hero" onPointerDown={handleStartNowPointerDown} onClick={handleStartNowClick}>
                ابدأ الآن
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
        <div className="mwj-waves pointer-events-none absolute inset-x-0 bottom-0">
          <svg
            className="mwj-waves__svg"
            viewBox="0 0 1200 120"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path className="mwj-waves__line mwj-waves__line--a" d="M0,70 C120,38 240,102 360,70 C480,38 600,102 720,70 C840,38 960,102 1080,70 C1140,54 1170,50 1200,52" />
            <path className="mwj-waves__line mwj-waves__line--b" d="M0,84 C140,58 260,110 400,84 C540,58 660,110 800,84 C940,58 1060,110 1200,84" />
            <path className="mwj-waves__line mwj-waves__line--c" d="M0,60 C150,30 260,92 420,60 C580,28 690,92 860,60 C1030,30 1120,78 1200,68" />
          </svg>
        </div>
      </section>

      <section className="mwj-gradient-subtle py-12 sm:py-20">
        <div className="container mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mb-8 text-center sm:mb-12">
            <h2 className="mb-2 text-xl font-bold sm:mb-3 sm:text-2xl md:text-3xl">كل ما تحتاجه في مكان واحد</h2>
            <p className="text-sm text-text-secondary-light dark:text-text-secondary-dark sm:text-base">
              ثمانية محاور أساسية لإدارة حضورك الرقمي
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 md:gap-6 lg:grid-cols-4">
            {services.map((service, index) => (
              <ServiceCard
                key={service.title}
                icon={service.icon}
                title={service.title}
                description={service.description}
                delay={index * 75}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="py-10 sm:py-16">
        <div className="container mx-auto max-w-4xl px-4 sm:px-6">
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
            {trustItems.map((item) => (
              <TrustBadge key={item.label} icon={item.icon} label={item.label} />
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border-light/50 py-6 dark:border-border-dark/50 sm:py-8">
        <div className="container mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center gap-3 sm:grid sm:grid-cols-3 sm:items-center">
            <div className="sm:justify-self-start">
              <Logo size="sm" />
            </div>
            <p className="text-center text-xs text-text-secondary-light dark:text-text-secondary-dark sm:text-sm">
            © 2026 MWJ. جميع الحقوق محفوظة.
            </p>
            <div className="hidden sm:block" />
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
