import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import LandingPage from './components/LandingPage';
import HomePage from './components/HomePage';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import './i18n';

function AppContent() {
  const navigate = useNavigate();

  useEffect(() => {
    const sessionString = localStorage.getItem('quantum_session');
    
    if (sessionString) {
      const session = JSON.parse(sessionString);
      const currentTime = new Date().getTime();

      // Check if current time has passed the 3-month expiration time
      if (currentTime > session.expiry) {
        localStorage.removeItem('quantum_session');
        navigate('/login');
      }
    }
  }, [navigate]);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
    </Routes>
  );
}

function App() {
  return (
    <LanguageProvider>
      <Router>
        <AppContent />
      </Router>
    </LanguageProvider>
  );
}

export default App;