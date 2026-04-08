import React, { useState } from 'react';
import { useAuth } from '../utils/AuthContext';
import './Auth.css';

function SignupPage({ onLoginClick, onSignupSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { signup } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      await signup(email, password);
      onSignupSuccess();
    } catch (err) {
      setError(err.message || 'Signup failed');
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
            <h1 className="auth-title">SIGN UP</h1>
            <p className="auth-tagline">Initialize your Gateway Key</p>
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
                placeholder="Developer Email"
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
                placeholder="Access Secret"
                minLength={6}
                disabled={loading}
                className="input-with-icon"
              />
            </div>

            <div className="input-wrapper">
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="Confirm Secret"
                minLength={6}
                disabled={loading}
                className="input-with-icon"
              />
            </div>

            <button 
              type="submit" 
              className="btn-login premium"
              disabled={loading}
            >
              {loading ? 'GENERATING PROTOCOL...' : 'GENERATE KEY'}
            </button>
          </form>

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <button 
              onClick={onLoginClick}
              className="link-button"
              disabled={loading}
            >
              Log in
            </button>
          </p>
        </div>
        </div>
    </div>
  );
}

export default SignupPage;
