import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const LandingPage = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  return (
    <div className="landing-wrapper">
      {/* Top Navbar */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="landing-logo-badge">QM</span> {t('appName')}
        </div>

        <div className="landing-nav-right">
          {/* Language Switcher */}
          <div className="lang-selector-group">
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

          <button className="nav-btn-secondary" onClick={() => navigate('/login')}>
            {t('loginNav')}
          </button>
          <button className="nav-btn-primary" onClick={() => navigate('/register')}>
            {t('registerNav')}
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="landing-hero">
        <div className="hero-badge">
          Quantum & AI Clinical Telemetry
        </div>
        <h1 className="hero-headline">
          {t('landingTitle')}
        </h1>
        <p className="hero-subtext">
          {t('landingSubtitle')}
        </p>
        <div className="hero-cta-group">
          <button className="cta-btn-main" onClick={() => navigate('/login')}>
            {t('getStarted')}
          </button>
          <button className="cta-btn-outline" onClick={() => navigate('/login')}>
            {t('explorePredictors')}
          </button>
        </div>
      </header>

      {/* Features Grid */}
      <section className="landing-features-section">
        <h2 className="section-heading">{t('featuresTitle')}</h2>
        
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#08F1D9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
            </div>
            <h3 className="feature-title">{t('feature1Title')}</h3>
            <p className="feature-desc">{t('feature1Desc')}</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#08F1D9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
            </div>
            <h3 className="feature-title">{t('feature2Title')}</h3>
            <p className="feature-desc">{t('feature2Desc')}</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#08F1D9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
            </div>
            <h3 className="feature-title">{t('feature3Title')}</h3>
            <p className="feature-desc">{t('feature3Desc')}</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
            </div>
            <h3 className="feature-title">{t('feature4Title')}</h3>
            <p className="feature-desc">{t('feature4Desc')}</p>
          </div>
        </div>
      </section>


      {/* Footer */}
      <footer className="landing-footer">
        <div>© 2026 {t('appName')} Medical Diagnostics Platform. All rights reserved.</div>
        <div style={{ color: '#07A3B2', fontWeight: 600 }}>Healthcare Grade • End-to-End Encrypted</div>
      </footer>
    </div>
  );
};

export default LandingPage;