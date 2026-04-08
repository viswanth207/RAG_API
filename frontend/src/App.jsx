import React, { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './utils/AuthContext'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import ApiGatewayPage from './pages/ApiGatewayPage'

function AppContent() {
  const [currentPage, setCurrentPage] = useState('landing')

  const { user, loading, logout, isAuthenticated } = useAuth()

  const navigateToLanding = () => {
    setCurrentPage('landing')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const navigateToLogin = () => {
    setCurrentPage('login')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const navigateToSignup = () => {
    setCurrentPage('signup')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleLogout = async () => {
    await logout()
    navigateToLanding()
  }

  const navigateToApi = () => {
    if (!isAuthenticated) {
      setCurrentPage('login')
      return
    }
    setCurrentPage('api')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Only block for a maximum of 2 seconds for a better user experience
  const [showSpinner, setShowSpinner] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setShowSpinner(false), 2000);
    return () => clearTimeout(timer);
  }, [loading]);

  if (loading && showSpinner && currentPage !== 'landing') {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Connecting to BRAIN.OS Protocols...</p>
      </div>
    )
  }

  return (
    <>
      <Navbar
        onHomeClick={navigateToLanding}
        onApiGatewayClick={navigateToApi}
        onLoginClick={navigateToLogin}
        onLogoutClick={handleLogout}
        user={user}
        isAuthenticated={isAuthenticated}
      />
      <div className={currentPage === 'api' ? "api-full-content" : "app-content"}>
        {currentPage === 'landing' && (
          <LandingPage onGetStarted={() => setCurrentPage(isAuthenticated ? 'api' : 'login')} />
        )}
        {currentPage === 'login' && (
          <LoginPage
            onSignupClick={navigateToSignup}
            onLoginSuccess={() => setCurrentPage('api')}
          />
        )}
        {currentPage === 'signup' && (
          <SignupPage
            onLoginClick={navigateToLogin}
            onSignupSuccess={() => setCurrentPage('api')}
          />
        )}
        {currentPage === 'api' && (
          <ApiGatewayPage onHomeClick={navigateToLanding} />
        )}
      </div>
    </>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
