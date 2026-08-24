import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [formData, setFormData] = useState({
    fullName: '',
    gender: '',
    age: '',
    phone: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');


  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.gender) {
      setError("Please select your gender.");
      return;
    }

    if (!formData.age) {
      setError("Please enter your age.");
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match!");
      return;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);

    try {
      const data = await api.register({
        fullName: formData.fullName,
        email: formData.email,
        password: formData.password,
        gender: formData.gender,
        age: parseInt(formData.age) || 25,
        phone: formData.phone
      });

      // 90 days validity (3 months)
      const expiresInHours = 24 * 90;
      const expirationTime = new Date().getTime() + (expiresInHours * 60 * 60 * 1000);

      const userProfile = data.user || {
        name: formData.fullName,
        email: formData.email,
        gender: formData.gender,
        age: parseInt(formData.age) || 25,
        phone: formData.phone
      };

      const sessionData = {
        token: data.access_token || 'registered_token',
        user: userProfile,
        expiry: expirationTime,
        created: new Date().getTime()
      };

      localStorage.setItem('quantum_session', JSON.stringify(sessionData));
      localStorage.setItem('quantum_user_profile', JSON.stringify(userProfile));

      setSuccess("Account registered successfully! Launching your medical dashboard...");
      setTimeout(() => {
        navigate('/home');
      }, 1000);
    } catch (err) {
      console.error("Registration error:", err);
      setError(err.message || "Registration failed. Please check your details.");
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

      <div className="auth-card-modern" style={{ maxWidth: '520px' }}>
        <div className="auth-brand-header" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <div className="auth-logo-badge">QM</div>
          <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800, color: '#063940' }}>
            {t('appName')}
          </h1>
        </div>

        <h2 className="auth-title">{t('registerTitle')}</h2>
        <p className="auth-subtitle">{t('registerSubtitle')}</p>

        {error && (
          <div className="auth-error-badge">
            {error}
          </div>
        )}

        {success && (
          <div style={{ background: '#dcfce7', border: '1px solid #22c55e', color: '#15803d', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.88rem', fontWeight: 'bold' }}>
            {success}
          </div>
        )}


        <form onSubmit={handleRegister} autoComplete="off" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="field-label">{t('fullName')}</label>
            <input 
              type="text" 
              name="reg_fullname"
              id="reg_fullname"
              placeholder="Enter your full name" 
              value={formData.fullName}
              onChange={(e) => setFormData({...formData, fullName: e.target.value})}
              className="form-input" 
              autoComplete="off"
              disabled={loading}
              required 
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label className="field-label">{t('gender')}</label>
              <select 
                value={formData.gender}
                onChange={(e) => setFormData({...formData, gender: e.target.value})}
                className="form-input" 
                disabled={loading}
                required
              >
                <option value="">Select Gender</option>
                <option value="Male">{t('male')}</option>
                <option value="Female">{t('female')}</option>
                <option value="Other">{t('other')}</option>
              </select>
            </div>
            <div>
              <label className="field-label">{t('age')}</label>
              <input 
                type="number" 
                name="reg_age"
                id="reg_age"
                placeholder="Enter your age" 
                value={formData.age}
                onChange={(e) => setFormData({...formData, age: e.target.value})}
                className="form-input" 
                autoComplete="off"
                disabled={loading}
                required 
                min="1"
                max="120"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label className="field-label">{t('email')}</label>
              <input 
                type="email" 
                name="reg_email"
                id="reg_email"
                placeholder="Enter your email address" 
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="form-input" 
                autoComplete="off"
                disabled={loading}
                required 
              />
            </div>
            <div>
              <label className="field-label">{t('phone')}</label>
              <input 
                type="tel" 
                name="reg_phone"
                id="reg_phone"
                placeholder="Enter your phone number" 
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="form-input" 
                autoComplete="off"
                disabled={loading}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label className="field-label">{t('password')}</label>
              <div style={{ position: 'relative' }}>
                <input 
                  type={showPassword ? "text" : "password"} 
                  name="reg_password"
                  id="reg_password"
                  placeholder="Enter your password" 
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
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
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <div>
              <label className="field-label">{t('confirmPassword')}</label>
              <div style={{ position: 'relative' }}>
                <input 
                  type={showConfirmPassword ? "text" : "password"} 
                  name="reg_confirm_password"
                  id="reg_confirm_password"
                  placeholder="Confirm your password" 
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                  className="form-input" 
                  style={{ paddingRight: '44px' }}
                  autoComplete="new-password"
                  disabled={loading}
                  required 
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
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
                  title={showConfirmPassword ? "Hide password" : "Show password"}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>




          <button 
            type="submit" 
            className="submit-predictor-btn"
            disabled={loading}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'Creating Account...' : t('registerBtn')}
          </button>

        </form>

        <div className="auth-footer-text">
          {t('alreadyAccount')}{' '}
          <span onClick={() => navigate('/login')} className="auth-link">
            {t('logInLink')}
          </span>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;