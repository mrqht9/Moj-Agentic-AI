import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import ChatInterface from './components/ChatInterface'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Register from './pages/Register'
import Profile from './pages/Profile'
import AdminDashboard from './pages/AdminDashboard'
import LandingPage from './pages/LandingPage'

function App() {
  const [darkMode, setDarkMode] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  // Check if user is logged in (from localStorage)
  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const handleRegister = (userData) => {
    setUser(userData)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('user')
  }

  const AuthLayout = () => {
    if (!user) return <Navigate to="/login" replace />

    return (
      <div className="flex h-screen w-full overflow-hidden">
        <Sidebar
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          user={user}
          onLogout={handleLogout}
        />
        <div className="w-px bg-border-light dark:bg-border-dark"></div>
        <div className="flex-1 h-full overflow-y-auto">
          <Outlet />
        </div>
      </div>
    )
  }

  return (
    <Router>
      <div className="min-h-screen bg-background-light dark:bg-background-dark">
        <Routes>
          <Route
            path="/"
            element={
              <LandingPage
                darkMode={darkMode}
                setDarkMode={setDarkMode}
                user={user}
                onLogout={handleLogout}
              />
            }
          />
          <Route path="/auth" element={<Navigate to="/login" replace />} />
          <Route 
            path="/login" 
            element={
              user ? <Navigate to="/chat" replace /> : <Login onLogin={handleLogin} />
            } 
          />
          <Route 
            path="/register" 
            element={
              user ? <Navigate to="/chat" replace /> : <Register onRegister={handleRegister} />
            } 
          />
          <Route element={<AuthLayout />}>
            <Route
              path="/chat"
              element={
                <ChatInterface
                  darkMode={darkMode}
                  setDarkMode={setDarkMode}
                  user={user}
                />
              }
            />
            <Route
              path="/profile"
              element={
                <Profile
                  user={user}
                  setUser={setUser}
                  darkMode={darkMode}
                />
              }
            />
          </Route>
          <Route 
            path="/admin" 
            element={
              user?.is_admin ? (
                <AdminDashboard 
                  user={user}
                  darkMode={darkMode}
                />
              ) : (
                <Navigate to="/chat" replace />
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  )
}

export default App
