import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.includes('@')) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);

    try {
      const data = await api.login(email, password);

      // Set session duration to 90 days
      const expiresInHours = 24 * 90;
      const expirationTime = new Date().getTime() + (expiresInHours * 60 * 60 * 1000);

      const sessionData = {
        token: data.access_token,
        user: data.user || { email, name: email.split('@')[0] },
        expiry: expirationTime
      };

      localStorage.setItem('quantum_session', JSON.stringify(sessionData));
      navigate('/home');
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
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
            <input 
              type="password" 
              name="quantum_password_field"
              id="quantum_password_field"
              placeholder="Enter your password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="form-input" 
              autoComplete="new-password"
              disabled={loading}
              required 
            />
          </div>

          <button 
            type="submit" 
            className="submit-predictor-btn"
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Authenticating...' : t('loginBtn')}
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