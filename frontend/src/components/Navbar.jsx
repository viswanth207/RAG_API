import React, { useState, useRef, useEffect } from 'react'
import './Navbar.css'

function Navbar({ onHomeClick, onApiGatewayClick, onLoginClick, onLogoutClick, user, isAuthenticated }) {
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const profileRef = useRef(null)

  const toggleProfileMenu = () => {
    setProfileMenuOpen(!profileMenuOpen)
  }

  const handleProfileMenuClick = (action) => {
    setProfileMenuOpen(false)
    action()
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <nav className="navbar">
      <div className="nav-container">
          <div className="nav-logo premium-logo" onClick={onHomeClick}>
          <div className="logo-mark">
            <div className="logo-dot"></div>
          </div>
          <span className="logo-text">Data Mind <span className="logo-text-light">Gateway</span></span>
        </div>
        
        <div className="nav-links">
          {isAuthenticated ? (
            <>
              <a 
                href="#" 
                className="nav-link nav-link-cta" 
                onClick={(e) => { e.preventDefault(); onApiGatewayClick(); }}
              >
                Developer Hub
              </a>
              
              <div className="nav-profile" ref={profileRef}>
                <button className="profile-icon" onClick={toggleProfileMenu}>
                  <span className="profile-avatar">
                    {user?.email?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </button>
                
                {profileMenuOpen && (
                  <div className="profile-dropdown">
                    <div className="profile-dropdown-header">
                      <div className="profile-avatar-large">
                        {user?.email?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="profile-info">
                        <div className="profile-email">{user?.email}</div>
                      </div>
                    </div>
                    
                    <div className="profile-dropdown-divider"></div>
                    
                    <button 
                      className="profile-dropdown-item"
                      onClick={() => handleProfileMenuClick(onApiGatewayClick)}
                    >
                      <span className="dropdown-icon">🔑</span>
                      API Gateway
                    </button>
                    
                    <div className="profile-dropdown-divider"></div>
                    
                    <button 
                      className="profile-dropdown-item logout"
                      onClick={() => handleProfileMenuClick(onLogoutClick)}
                    >
                      <span className="dropdown-icon">🚪</span>
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <a 
              href="#" 
              className="nav-link nav-link-cta" 
              onClick={(e) => { e.preventDefault(); onLoginClick(); }}
            >
              Login
            </a>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
