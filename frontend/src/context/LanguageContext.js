import React, { createContext, useState, useContext } from 'react';

const translations = {
  en: {
    title: "Quantum Med AI",
    titleSpan: "AI",
    subtitle: "A new frontier in AI-powered medical diagnostics and patient care.",
    getStarted: "Get Started",
    chat: "Chat",
    medicalHistory: "Medical History",
    reports: "Reports",
    settings: "Settings",
    logout: "Logout",
    emergency: "EMERGENCY",
    placeholder: "Ask about symptoms, reports, or treatment...",
    send: "Send",
    selectLanguage: "Select Language"
  },
  te: {
    title: "Quantum Med AI",
    titleSpan: "AI",
    subtitle: "AI-ఆధారిత వైద్య నిర్ధారణ మరియు రోగి సంరక్షణలో ఒక కొత్త సరిహద్దు.",
    getStarted: "ప్రారంభించండి",
    chat: "చాట్",
    medicalHistory: "వైద్య చరిత్ర",
    reports: "నివేదికలు",
    settings: "సెట్టింగ్‌లు",
    logout: "లాగ్ అవుట్",
    emergency: "అత్యవసర పరిస్థితి",
    placeholder: "లక్షణాలు, నివేదికలు లేదా చికిత్స గురించి అడగండి...",
    send: "పంపు",
    selectLanguage: "భాషను ఎంచుకోండి"
  },
  hi: {
    title: "Quantum Med AI",
    titleSpan: "एआई",
    subtitle: "एआई-संचालित चिकित्सा निदान और रोगी देखभाल में एक नया कदम।",
    getStarted: "शुरू करें",
    chat: "चैट",
    medicalHistory: "चिकित्सा इतिहास",
    reports: "रिपोर्ट",
    settings: "सेटिंग्स",
    logout: "लॉग आउट",
    emergency: "आपातकालीन",
    placeholder: "लक्षणों, रिपोर्ट या उपचार के बारे में पूछें...",
    send: "भेजें",
    selectLanguage: "भाषा चुनें"
  }
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState('en');

  const t = (key) => translations[lang][key] || key;

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);