import React, { useState } from 'react';
import { useAuth } from '../utils/AuthContext';
import './Auth.css';

function LoginPage({ onSignupClick, onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      onLoginSuccess();
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="noise-overlay"></div>
      
        <div className="auth-card modern">
          <div className="auth-logo">
            <div className="logo-circle abstract"></div>
            <h1 className="auth-title">LOGIN</h1>
            <p className="auth-tagline">Intelligence Gateway Protocol</p>
          </div>
        
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form modern">
            <div className="input-wrapper">
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="Username / Email"
                disabled={loading}
                className="input-with-icon"
              />
            </div>

            <div className="input-wrapper">
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Password"
                minLength={6}
                disabled={loading}
                className="input-with-icon"
              />
            </div>

            <div className="auth-options">
              <label className="remember-me">
                <input type="checkbox" />
                <span>Remember Session</span>
              </label>
              <button type="button" className="forgot-password">Recover Key</button>
            </div>

            <button 
              type="submit" 
              className="btn-login premium"
              disabled={loading}
            >
              {loading ? 'AUTHENTICATING...' : 'INITIALIZE'}
            </button>
          </form>

        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <button 
              onClick={onSignupClick}
              className="link-button"
              disabled={loading}
            >
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
