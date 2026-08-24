import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');


  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    const cleanEmail = (email || '').trim().toLowerCase();

    if (!cleanEmail.includes('@')) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);

    try {
      let data;
      try {
        data = await api.login(cleanEmail, password);
      } catch (apiErr) {
        // Fallback: Check local device registry (recovers user if Render container restarted/rebuilt)
        const localRegistry = JSON.parse(localStorage.getItem('quantum_registered_users') || '{}');
        const localUser = localRegistry[cleanEmail];

        if (localUser && localUser.password === password) {
          data = {
            access_token: 'quantum_resilient_token_' + Date.now(),
            user: {
              name: localUser.fullName,
              email: cleanEmail,
              gender: localUser.gender,
              age: localUser.age,
              phone: localUser.phone
            }
          };

          // Re-sync with backend in background so database is re-populated
          api.register({
            fullName: localUser.fullName,
            email: cleanEmail,
            password: password,
            gender: localUser.gender,
            age: localUser.age,
            phone: localUser.phone
          }).catch(() => {});
        } else if (cleanEmail === 'demo@quantummed.ai' && (password === 'password123' || password === 'demo123')) {
          data = {
            access_token: 'quantum_demo_token',
            user: {
              name: 'Quantum Medical Demo',
              email: cleanEmail,
              gender: 'Female',
              age: 28,
              phone: '9876543210'
            }
          };
        } else {
          throw apiErr;
        }
      }

      // Set session duration to 90 days
      const expiresInHours = 24 * 90;
      const expirationTime = new Date().getTime() + (expiresInHours * 60 * 60 * 1000);

      const sessionData = {
        token: data.access_token || 'quantum_token',
        user: data.user || { email: cleanEmail, name: cleanEmail.split('@')[0] },
        expiry: expirationTime
      };

      localStorage.setItem('quantum_session', JSON.stringify(sessionData));
      localStorage.setItem('quantum_user_profile', JSON.stringify(sessionData.user));
      navigate('/home');
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleUseDemoAccount = () => {
    setEmail('demo@quantummed.ai');
    setPassword('password123');
    setError('');
  };

  return (
    <div className="auth-wrapper">
      {/* Top Floating Language Switcher */}
      <div className="auth-lang-float">
        <div className="lang-selector-group" style={{ background: 'rgba(255, 255, 255, 0.95)' }}>
          <button 
            type="button"
            className={`lang-pill-btn ${i18n.language === 'en' ? 'active' : ''}`}
            onClick={() => i18n.changeLanguage('en')}
          >
            EN
          </button>
          <button 
            type="button"
            className={`lang-pill-btn ${i18n.language === 'te' ? 'active' : ''}`}
            onClick={() => i18n.changeLanguage('te')}
          >
            తెలుగు
          </button>
          <button 
            type="button"
            className={`lang-pill-btn ${i18n.language === 'hi' ? 'active' : ''}`}
            onClick={() => i18n.changeLanguage('hi')}
          >
            हिंदी
          </button>
        </div>
      </div>

      <div className="auth-card-modern">
        <div className="auth-brand-header" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <div className="auth-logo-badge">QM</div>
          <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800, color: '#063940' }}>
            {t('appName')}
          </h1>
        </div>

        <h2 className="auth-title">{t('loginTitle')}</h2>
        <p className="auth-subtitle">{t('loginSubtitle')}</p>

        {error && (
          <div className="auth-error-badge">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} autoComplete="off" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label className="field-label">{t('email')}</label>
            <input 
              type="email" 
              name="quantum_email_field"
              id="quantum_email_field"
              placeholder="Enter your email address" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="form-input" 
              autoComplete="off"
              disabled={loading}
              required 
            />
          </div>

          <div>
            <label className="field-label">{t('password')}</label>
            <div style={{ position: 'relative' }}>
              <input 
                type={showPassword ? "text" : "password"} 
                name="quantum_password_field"
                id="quantum_password_field"
                placeholder="Enter your password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="form-input" 
                style={{ paddingRight: '44px' }}
                autoComplete="new-password"
                disabled={loading}
                required 
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#64748b'
                }}
                title={showPassword ? "Hide password" : "Show password"}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                )}
              </button>
            </div>
          </div>


          <button 
            type="submit" 
            className="submit-predictor-btn"
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Authenticating...' : t('loginBtn')}
          </button>

          <button
            type="button"
            onClick={handleUseDemoAccount}
            style={{
              background: '#f1f5f9',
              border: '1px dashed #94a3b8',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#334155',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <span>💡 Click to Fill Demo Account</span>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>(demo@quantummed.ai)</span>
          </button>
        </form>

        <div className="auth-footer-text">
          {t('dontHaveAccount')}{' '}
          <span onClick={() => navigate('/register')} className="auth-link">
            {t('registerLink')}
          </span>
        </div>
      </div>

    </div>
  );
};

export default LoginPage;