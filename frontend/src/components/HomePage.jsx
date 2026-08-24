import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import EmergencyAssistant from "./EmergencyAssistant";
import DiseasePredictors from "./DiseasePredictors";
import HospitalMap from "./HospitalMap";
import OfflineEmergencySuite from "./OfflineEmergencySuite";
import { api } from "../services/api";



const HomePage = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  
  // Chat state
  const [messages, setMessages] = useState([
    { sender: 'ai', text: t('welcome') }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceCallActive, setIsVoiceCallActive] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  
  // Emergency Modal
  const [emergencyModalOpen, setEmergencyModalOpen] = useState(false);

  // History & Reports state
  const [historyRecords, setHistoryRecords] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Profiles
  const [profiles, setProfiles] = useState([
    { name: 'Patient (Primary)', age: 25, gender: 'Female', active: true }
  ]);
  const [showAddPersonModal, setShowAddPersonModal] = useState(false);
  const [newPerson, setNewPerson] = useState({ name: '', age: '', gender: '' });

  const [profileFormData, setProfileFormData] = useState({
    name: '',
    email: '',
    age: '32',
    gender: 'Male',
    phone: '',
    bloodGroup: 'O+ve',
    weight: '68',
    height: '172',
    trestbps: '120',
    allergies: 'None recorded',
    chronicConditions: 'None recorded'
  });
  const [profileSaveSuccess, setProfileSaveSuccess] = useState('');
  const [sessionExpiryDate, setSessionExpiryDate] = useState('');

  const fileInputRef = useRef(null);
  const speechUtteranceRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Load User Session & Check Auth (Valid for 90 Days / 3 Months)
  useEffect(() => {
    const sessionString = localStorage.getItem('quantum_session');
    if (!sessionString) {
      navigate('/login');
      return;
    }

    try {
      const session = JSON.parse(sessionString);
      if (new Date().getTime() > session.expiry) {
        localStorage.removeItem('quantum_session');
        navigate('/login');
        return;
      }
      
      let userObj = session.user || {};
      const cachedProfile = localStorage.getItem('quantum_user_profile');
      if (cachedProfile) {
        try {
          userObj = { ...userObj, ...JSON.parse(cachedProfile) };
        } catch (err) {}
      }

      setCurrentUser(userObj);
      setProfileFormData({
        name: userObj.name || userObj.fullName || '',
        email: userObj.email || '',
        age: userObj.age || '32',
        gender: userObj.gender || 'Male',
        phone: userObj.phone || '',
        bloodGroup: userObj.bloodGroup || 'O+ve',
        weight: userObj.weight || '68',
        height: userObj.height || '172',
        trestbps: userObj.trestbps || '120',
        allergies: userObj.allergies || 'None recorded',
        chronicConditions: userObj.chronicConditions || 'None recorded'
      });

      if (session.expiry) {
        setSessionExpiryDate(new Date(session.expiry).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        }));
      }

      if (userObj.name) {
        setProfiles([
          { name: userObj.name, age: userObj.age || 25, gender: userObj.gender || 'Not specified', active: true }
        ]);
      }
    } catch (e) {
      localStorage.removeItem('quantum_session');
      navigate('/login');
    }
  }, [navigate]);

  const handleSaveProfile = (e) => {
    e.preventDefault();
    const updatedUser = {
      ...currentUser,
      ...profileFormData
    };
    setCurrentUser(updatedUser);
    localStorage.setItem('quantum_user_profile', JSON.stringify(profileFormData));

    const sessionString = localStorage.getItem('quantum_session');
    if (sessionString) {
      try {
        const session = JSON.parse(sessionString);
        session.user = updatedUser;
        localStorage.setItem('quantum_session', JSON.stringify(session));
      } catch (err) {}
    }

    localStorage.setItem('quantum_offline_medical_id', JSON.stringify({
      fullName: profileFormData.name,
      bloodGroup: profileFormData.bloodGroup,
      age: profileFormData.age,
      allergies: profileFormData.allergies,
      chronicConditions: profileFormData.chronicConditions,
      emergencyContactName: 'Primary Guardian',
      emergencyContactPhone: profileFormData.phone || '+91 98765 43210',
      organDonor: 'Yes'
    }));

    setProfileSaveSuccess('Patient Profile and clinical vitals saved! All disease predictors & emergency passes are now pre-filled.');
    setTimeout(() => setProfileSaveSuccess(''), 4000);
  };


  // Online / Offline monitor
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Fetch Medical History from Backend
  const fetchHistory = async () => {
    if (!currentUser?.email) return;
    setHistoryLoading(true);
    try {
      const records = await api.getHistory(currentUser.email);
      setHistoryRecords(records);
    } catch (err) {
      console.error("Error fetching medical history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser?.email && (activeTab === 'history' || activeTab === 'reports')) {
      fetchHistory();
    }
  }, [activeTab, currentUser]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, selectedFile]);

  const [selectedFilePreview, setSelectedFilePreview] = useState(null);
  const [voices, setVoices] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const recognitionRef = useRef(null);

  // Pre-load natural system voices
  useEffect(() => {
    const loadVoices = () => {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        const available = window.speechSynthesis.getVoices();
        setVoices(available);
      }
    };
    loadVoices();
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => setSelectedFilePreview(ev.target.result);
        reader.readAsDataURL(file);
      } else {
        setSelectedFilePreview(null);
      }
    }
  };

  const handleClearSelectedFile = () => {
    setSelectedFile(null);
    setSelectedFilePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Clean Markdown & Medical Abbreviations for Natural Speech Synthesis
  const cleanTextForSpeech = (text) => {
    if (!text) return '';
    return text
      .replace(/[#*_`>~-]/g, ' ')
      .replace(/\[.*?\]/g, ' ')
      .replace(/[\u{1F600}-\u{1F6FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F300}-\u{1F5FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1F004}\u{1F0CF}]/gu, '')
      .replace(/\bBP\b/g, 'Blood Pressure')
      .replace(/\bmg\/dL\b/g, 'milligrams per deciliter')
      .replace(/\bg\/dL\b/g, 'grams per deciliter')
      .replace(/\b1-0-1\b/g, 'morning and night')
      .replace(/\b1-1-1\b/g, 'morning, afternoon and night')
      .replace(/\bRx\b/g, 'Prescription')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Safe Speech Recognition Engine with Live Transcript
  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in your browser. Please use Chrome or Edge.");
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }

    try {
      const recognition = new SpeechRecognition();
      const currentLang = i18n.language;
      recognition.lang = currentLang === 'hi' ? 'hi-IN' : currentLang === 'te' ? 'te-IN' : 'en-US';
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
        setInterimTranscript('');
      };

      recognition.onresult = (event) => {
        let finalTranscript = '';
        let currentInterim = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            currentInterim += event.results[i][0].transcript;
          }
        }

        if (currentInterim) {
          setInterimTranscript(currentInterim);
        }

        if (finalTranscript) {
          setIsListening(false);
          setInterimTranscript('');
          processUserMessage(finalTranscript, true);
        }
      };

      recognition.onerror = (err) => {
        console.warn("Speech recognition error:", err.error);
        setIsListening(false);
        setInterimTranscript('');
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Speech recognition startup error:", err);
      setIsListening(false);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }
    setIsListening(false);
    setInterimTranscript('');
  };

  // Toggle Continuous Hands-Free Voice Assistant Call Mode
  const toggleVoiceAssistant = () => {
    const newState = !isVoiceCallActive;
    setIsVoiceCallActive(newState);
    if (newState) {
      startListening();
    } else {
      stopSpeaking();
      stopListening();
    }
  };

  // Text-to-Speech Output with Natural Voice Selection
  const speakAiResponse = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    const cleanText = cleanTextForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const currentLang = i18n.language;
    utterance.lang = currentLang === 'hi' ? 'hi-IN' : currentLang === 'te' ? 'te-IN' : 'en-US';
    
    // Select highest quality natural voice
    const voiceList = voices.length > 0 ? voices : window.speechSynthesis.getVoices();
    const matchedVoice = voiceList.find(v => v.lang.startsWith(currentLang) && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Neural') || v.name.includes('Online'))) ||
                         voiceList.find(v => v.lang.startsWith(currentLang)) ||
                         voiceList[0];
    
    if (matchedVoice) utterance.voice = matchedVoice;
    utterance.rate = 1.02;
    utterance.pitch = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => {
      setIsSpeaking(false);
      if (isVoiceCallActive) {
        setTimeout(() => startListening(), 400);
      }
    };
    utterance.onerror = () => setIsSpeaking(false);

    speechUtteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const cleanAiDisplayMessage = (raw) => {
    if (!raw) return '';
    let s = String(raw).trim();
    const match = s.match(/"ai_reply"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)/);
    if (match && match[1]) {
      s = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n');
    }
    s = s.replace(/^\s*\{\s*"ai_reply"\s*:\s*"?/, '');
    s = s.replace(/"?\s*,\s*"(?:doctor|is_emergency|matched_keywords|detected_diseases|risk_level|recommendation)".*$/s, '');
    s = s.replace(/["\}]\s*$/, '');
    return s.trim();
  };

  // Process message and send to Backend API
  const processUserMessage = async (textToSend, isVoiceInput = false) => {

    if (!textToSend.trim() && !selectedFile) return;
    if (isOffline) return;

    // If user typed in text, ensure any prior speech is stopped immediately
    if (!isVoiceInput && !isVoiceCallActive) {
      stopSpeaking();
    }

    const currentFile = selectedFile;
    const currentPreview = selectedFilePreview;
    const userEmail = currentUser?.email || 'guest@quantummed.ai';
    const displayMsg = textToSend.trim() || (currentFile ? `Attached: ${currentFile.name}` : '');

    setMessages((prev) => [
      ...prev, 
      { 
        sender: 'user', 
        text: displayMsg, 
        imagePreview: currentPreview 
      }
    ]);
    
    setInputMessage('');
    handleClearSelectedFile();
    setIsLoading(true);

    try {
      let data;
      if (currentPreview) {
        data = await api.analyzeSymptoms({
          text: textToSend || 'Please review and analyze this attached medical document.',
          user_email: userEmail,
          document_name: currentFile ? currentFile.name : null,
          image_base64: currentPreview,
          mime_type: currentFile ? currentFile.type : 'image/jpeg',
          language: i18n.language
        });
      } else {
        data = await api.analyzeSymptoms({
          text: textToSend || (currentFile ? `Report uploaded: ${currentFile.name}` : ''),
          user_email: userEmail,
          document_name: currentFile ? currentFile.name : null,
          language: i18n.language
        });
      }

      setIsLoading(false);

      if (data.is_emergency) {
        setMessages((prev) => [
          ...prev,
          { 
            sender: 'ai', 
            text: `🚨 CRITICAL EMERGENCY INDICATOR DETECTED!\nOpening Emergency Triage Assistant immediately...`,
            isEmergency: true
          }
        ]);
        setEmergencyModalOpen(true);
        if (isVoiceInput || isVoiceCallActive) {
          speakAiResponse("Critical emergency condition detected. Opening Emergency Assistant.");
        }
        return;
      }

      const cleanReply = cleanAiDisplayMessage(data.ai_reply);

      setMessages((prev) => [
        ...prev,
        { 
          sender: 'ai', 
          text: cleanReply,
          doctor: data.doctor,
          risk: data.risk_level,
          visionData: data.vision_data || null
        }
      ]);

      // Only speak aloud if the user initiated via Mic or Voice Assistant Mode
      if (isVoiceInput || isVoiceCallActive) {
        speakAiResponse(cleanReply);
      }


    } catch (err) {
      console.error("Chat analysis API error:", err);
      setIsLoading(false);
      
      const fallbackReply = "Your inquiry was received. Please consult a qualified medical professional for clinical diagnosis.";
      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: fallbackReply }
      ]);
      if (isVoiceInput || isVoiceCallActive) {
        speakAiResponse(fallbackReply);
      }
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    processUserMessage(inputMessage, false); // Typed text is silent
  };



  const handleLogout = () => {
    localStorage.removeItem('quantum_session');
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    navigate('/login');
  };

  const handleAddPersonSubmit = (e) => {
    e.preventDefault();
    if (!newPerson.name || !newPerson.age || !newPerson.gender) return;
    setProfiles([...profiles, { ...newPerson, active: false }]);
    setNewPerson({ name: '', age: '', gender: '' });
    setShowAddPersonModal(false);
  };

  // Compute reports statistics
  const totalAssessments = historyRecords.length;
  const highRiskCount = historyRecords.filter(r => r.result?.toLowerCase().includes('high') || r.result?.toLowerCase().includes('critical')).length;
  const moderateRiskCount = historyRecords.filter(r => r.result?.toLowerCase().includes('mod') || r.result?.toLowerCase().includes('medium')).length;
  const lowRiskCount = totalAssessments - highRiskCount - moderateRiskCount;

  return (
    <div className="home-container">
      
      {isOffline && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, background: '#ef4444', color: 'white', padding: '10px', textAlign: 'center', zIndex: 1000, fontWeight: 'bold', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px' }}>
          <span>⚠️ No internet connection detected. Please check your network.</span>
          <button onClick={() => window.location.reload()} style={{ background: 'white', color: '#ef4444', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            Retry
          </button>
        </div>
      )}

      {/* Sidebar Mobile Overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div>
          <div className="sidebar-logo">
            <span className="sidebar-logo-icon">QM</span> {t('appName')}
          </div>
          <div className="sidebar-profile-badge">
            <span>{t('activeProfile')}: <strong>{profiles.find(p => p.active)?.name || currentUser?.name || 'Patient'}</strong></span>
          </div>
          <ul className="sidebar-menu">
            <li className={activeTab === 'chat' ? 'active' : ''} onClick={() => { setActiveTab('chat'); setSidebarOpen(false); }}>
              {t('chatTab')}
            </li>
            <li className={activeTab === 'predictor' ? 'active' : ''} onClick={() => { setActiveTab('predictor'); setSidebarOpen(false); }}>
              {t('predictorTab')}
            </li>
            <li className={activeTab === 'hospitals' ? 'active' : ''} onClick={() => { setActiveTab('hospitals'); setSidebarOpen(false); }}>
              {t('navHospitals') || 'Hospital & ICU Map'}
            </li>
            <li className={activeTab === 'offline' ? 'active' : ''} onClick={() => { setActiveTab('offline'); setSidebarOpen(false); }}>
              Offline Suite (No Internet)
            </li>
            <li className={activeTab === 'history' ? 'active' : ''} onClick={() => { setActiveTab('history'); setSidebarOpen(false); }}>
              {t('historyTab')}
            </li>
            <li className={activeTab === 'reports' ? 'active' : ''} onClick={() => { setActiveTab('reports'); setSidebarOpen(false); }}>
              {t('reportsTab')}
            </li>
            <li className={activeTab === 'settings' ? 'active' : ''} onClick={() => { setActiveTab('settings'); setSidebarOpen(false); }}>
              {t('settingsTab')}
            </li>
            <li onClick={() => setShowAddPersonModal(true)} className="add-member-btn">
              + {t('addMember')}
            </li>
          </ul>
        </div>
        <div style={{ marginTop: 'auto', paddingTop: '20px' }}>
          <button 
            onClick={handleLogout}
            className="logout-btn"
          >
            {t('logout')} ({currentUser?.email?.split('@')[0]})
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <main className="chat-area">
        <div className="chat-header-bar">
          <div className="header-left-group">
            <button 
              className="mobile-menu-toggle-btn"
              onClick={() => setSidebarOpen(!sidebarOpen)} 
              title="Open Navigation Menu"
            >
              ☰
            </button>
            
            <h2 className="header-title">
              {activeTab === 'chat' && t('chatTab')}
              {activeTab === 'predictor' && t('predictorTab')}
              {activeTab === 'hospitals' && (t('navHospitals') || 'Hospital & ICU Map')}
              {activeTab === 'offline' && 'Offline Emergency Suite (Zero-Internet)'}
              {activeTab === 'history' && t('historyTab')}
              {activeTab === 'reports' && t('reportsTab')}
              {activeTab === 'settings' && t('settingsTab')}
            </h2>
          </div>

          <div className="header-right-controls">
            {/* Global Language Selector */}
            <div className="lang-selector-group">
              <button 
                type="button"
                className={`lang-pill-btn ${i18n.language === 'en' ? 'active' : ''}`}
                onClick={() => i18n.changeLanguage('en')}
                title="Switch to English"
              >
                EN
              </button>
              <button 
                type="button"
                className={`lang-pill-btn ${i18n.language === 'te' ? 'active' : ''}`}
                onClick={() => i18n.changeLanguage('te')}
                title="తెలుగులోకి మార్చండి"
              >
                తెలుగు
              </button>
              <button 
                type="button"
                className={`lang-pill-btn ${i18n.language === 'hi' ? 'active' : ''}`}
                onClick={() => i18n.changeLanguage('hi')}
                title="हिंदी में बदलें"
              >
                हिंदी
              </button>
            </div>

            {/* Offline Suite Quick Toggle */}
            <button
              type="button"
              className={`voice-call-toggle-btn ${activeTab === 'offline' ? 'active' : ''}`}
              onClick={() => setActiveTab(activeTab === 'offline' ? 'chat' : 'offline')}
              style={{ background: activeTab === 'offline' ? '#991b1b' : '#334155' }}
              title="Toggle Zero-Internet Mode"
            >
              <span>{activeTab === 'offline' ? 'Live Telemetry' : 'Offline Suite'}</span>
            </button>

            {/* Hands-Free Voice Doctor Call Mode */}
            <button
              type="button"
              className={`voice-call-toggle-btn ${isVoiceCallActive ? 'active' : ''}`}
              onClick={toggleVoiceAssistant}
              title="Toggle Hands-Free Voice Doctor Call Mode"
            >
              <span>{isVoiceCallActive ? 'End Call' : 'Voice Doctor'}</span>
            </button>

            <button 
              className="emergency-btn"
              onClick={() => setEmergencyModalOpen(true)}
            >
              {t('emergencyBtn')}
            </button>
          </div>
        </div>




        {/* Real-time Voice Call Banner with Audio Equalizer */}
        {isVoiceCallActive && (
          <div style={{ background: 'linear-gradient(135deg, #063940 0%, #0c4a6e 100%)', color: 'white', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#22c55e', display: 'inline-block', boxShadow: '0 0 8px #22c55e' }}></span>
              <strong style={{ fontSize: '0.9rem' }}>
                {i18n.language === 'te' ? '🎙️ డాక్టర్ వాయిస్ కాల్ యాక్టివ్‌గా ఉంది (తెలుగు)' : i18n.language === 'hi' ? '🎙️ डॉक्टर वॉइस कॉल सक्रिय है (हिंदी)' : '🎙️ Hands-Free Voice Doctor Call Active (English)'}
              </strong>
              <span style={{ fontSize: '0.82rem', opacity: 0.85 }}>
                {isListening ? 'Listening to your symptoms... 👂' : isSpeaking ? 'Dr. Quantum is speaking... 🗣️' : 'Speak naturally without typing.'}
              </span>
            </div>
            <button
              onClick={toggleVoiceAssistant}
              style={{ background: '#dc2626', color: 'white', border: 'none', padding: '6px 14px', borderRadius: '8px', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer' }}
            >
              Disconnect
            </button>
          </div>
        )}




        {/* Tab 1: AI Chat Consultation */}
        {activeTab === 'chat' && (
          <>
            <div className="chat-box">
              {messages.map((msg, index) => (
                <div key={index} className={msg.sender === 'user' ? 'chat-msg-user' : 'chat-msg-ai'}>
                  {msg.imagePreview && (
                    <div style={{ marginBottom: '8px' }}>
                      <img 
                        src={msg.imagePreview} 
                        alt="Attached Document" 
                        style={{ maxWidth: '100%', maxHeight: '200px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.3)', display: 'block' }} 
                      />
                    </div>
                  )}
                  
                  <div>{msg.text}</div>

                  {/* Vision Data Breakdown: Prescriptions */}
                  {msg.visionData?.prescriptions?.length > 0 && (
                    <div style={{ marginTop: '12px', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
                      <strong style={{ color: '#063940', fontSize: '0.9rem' }}>💊 Extracted Prescribed Medications:</strong>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                        {msg.visionData.prescriptions.map((rx, rIdx) => (
                          <div key={rIdx} style={{ background: 'white', padding: '8px 10px', borderRadius: '6px', fontSize: '0.82rem', border: '1px solid #e2e8f0' }}>
                            <strong style={{ color: '#07A3B2' }}>{rx.medicine_name}</strong> {rx.dosage && `(${rx.dosage})`} — {rx.frequency} {rx.timing && `[${rx.timing}]`} {rx.duration && `for ${rx.duration}`}
                            {rx.purpose && <div style={{ color: '#64748b', fontSize: '0.78rem' }}>Purpose: {rx.purpose}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Vision Data Breakdown: Lab Biomarkers */}
                  {msg.visionData?.lab_biomarkers?.length > 0 && (
                    <div style={{ marginTop: '12px', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
                      <strong style={{ color: '#063940', fontSize: '0.9rem' }}>🧪 Clinical Laboratory Biomarkers:</strong>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', marginTop: '6px' }}>
                        {msg.visionData.lab_biomarkers.map((bio, bIdx) => (
                          <div key={bIdx} style={{ background: 'white', padding: '6px 8px', borderRadius: '6px', fontSize: '0.8rem', border: '1px solid #e2e8f0' }}>
                            <div style={{ color: '#334155', fontWeight: 'bold' }}>{bio.parameter}</div>
                            <div style={{ fontSize: '0.95rem', fontWeight: 800, color: bio.status === 'High' ? '#b91c1c' : bio.status === 'Low' ? '#b45309' : '#15803d' }}>
                              {bio.value} {bio.unit}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Ref: {bio.reference_range} ({bio.status})</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Vision Data Breakdown: Abnormal Findings */}
                  {msg.visionData?.abnormal_findings?.length > 0 && (
                    <div style={{ marginTop: '10px', background: '#fee2e2', padding: '8px 12px', borderRadius: '6px', fontSize: '0.82rem', color: '#991b1b' }}>
                      <strong>⚠️ Notable Out-of-Range Markers:</strong> {msg.visionData.abnormal_findings.join(', ')}
                    </div>
                  )}

                  {msg.doctor && (
                    <div style={{ fontSize: '0.8rem', marginTop: '8px', fontWeight: 'bold', opacity: 0.9 }}>
                      👨‍⚕️ Specialist: {msg.doctor} {msg.risk && `(${msg.risk} Risk)`}
                    </div>
                  )}

                  {/* Disease Predictor Quick Navigation Action */}
                  {msg.sender === 'ai' && (msg.text?.includes('Predictor') || msg.text?.includes('Disease') || msg.doctor) && (
                    <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      <button
                        type="button"
                        onClick={() => setActiveTab('predictor')}
                        style={{
                          background: 'linear-gradient(135deg, #063940 0%, #07a3b2 100%)',
                          color: '#ffffff',
                          border: 'none',
                          padding: '6px 14px',
                          borderRadius: '6px',
                          fontSize: '0.82rem',
                          fontWeight: 'bold',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          boxShadow: '0 2px 6px rgba(7,163,178,0.3)'
                        }}
                      >
                        🩺 Open Disease Predictors Hub
                      </button>
                    </div>
                  )}


                  {/* Per-Message Listen Button for AI Responses */}
                  {msg.sender === 'ai' && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                      <button
                        type="button"
                        onClick={() => {
                          if (isSpeaking) {
                            stopSpeaking();
                          } else {
                            speakAiResponse(msg.text);
                          }
                        }}
                        style={{
                          background: 'rgba(7, 163, 178, 0.12)',
                          border: 'none',
                          color: '#063940',
                          fontSize: '0.78rem',
                          padding: '4px 10px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                        title="Listen to this medical explanation"
                      >
                        {isSpeaking ? 'Stop Audio' : 'Listen'}
                      </button>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="chat-msg-ai" style={{ fontStyle: 'italic', color: '#64748b' }}>
                  QuantumMedAI neural models are analyzing clinical parameters...
                </div>
              )}

              {/* Real-time Listening Indicator & Live Transcript */}
              {isListening && (
                <div style={{ textAlign: 'center', background: 'rgba(239, 68, 68, 0.08)', border: '1px dashed #ef4444', color: '#b91c1c', padding: '10px 16px', borderRadius: '10px', margin: '10px 0', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                  <span style={{ display: 'inline-block', width: '10px', height: '10px', background: '#ef4444', borderRadius: '50%' }}></span>
                  <span>Listening: <em>{interimTranscript || 'Speak now...'}</em></span>
                  <button 
                    type="button" 
                    onClick={stopListening} 
                    style={{ marginLeft: '10px', background: '#ef4444', color: 'white', border: 'none', padding: '3px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 'bold' }}
                  >
                    Cancel
                  </button>
                </div>
              )}

              {/* Floating Stop Speaking Pill */}
              {isSpeaking && (
                <div style={{ position: 'sticky', bottom: '10px', display: 'flex', justifyContent: 'center', zIndex: 10, marginTop: '8px' }}>
                  <button
                    type="button"
                    onClick={stopSpeaking}
                    style={{ background: '#ef4444', color: 'white', border: 'none', padding: '8px 18px', borderRadius: '20px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 12px rgba(239,68,68,0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    Stop Audio Output
                  </button>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Selected File Floating Preview Chip */}
            {selectedFile && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#e2e8f0', padding: '6px 14px', borderRadius: '16px', margin: '0 0 8px 12px', width: 'fit-content' }}>
                {selectedFilePreview ? (
                  <img src={selectedFilePreview} alt="thumb" style={{ width: '22px', height: '22px', borderRadius: '4px', objectFit: 'cover' }} />
                ) : (
                  <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#063940' }}>Doc:</span>
                )}
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#063940' }}>{selectedFile.name}</span>
                <button 
                  type="button" 
                  onClick={handleClearSelectedFile} 
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', fontWeight: 'bold', fontSize: '0.9rem', padding: '0 4px' }}
                >
                  ✕
                </button>
              </div>
            )}

            <div className="chat-input-wrapper">
              <form onSubmit={handleSendMessage} className="chat-input-container">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileSelect} 
                  style={{ display: 'none' }} 
                  accept=".pdf,image/*,.doc,.docx"
                />

                <button 
                  type="button" 
                  className="chat-action-btn" 
                  title="Attach medical report or prescription image"
                  onClick={() => fileInputRef.current.click()}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                  </svg>
                </button>

                <input 
                  type="text" 
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder={isListening ? "Listening to your voice..." : t('placeholder')}
                  className="chat-input-field"
                />

                <button 
                  type="button" 
                  onClick={() => {
                    if (isListening) {
                      stopListening();
                    } else {
                      startListening();
                    }
                  }}
                  className="mic-btn"
                  title={isListening ? "Stop Listening" : "Click to Speak"}
                  style={{ 
                    background: isListening ? '#ef4444' : 'transparent',
                    color: isListening ? '#ffffff' : '#063940',
                    border: 'none',
                    borderRadius: '50%',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: isListening ? '0 0 10px #ef4444' : 'none',
                    transition: '0.2s',
                    flexShrink: 0
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="2" width="6" height="11" rx="3"></rect>
                    <path d="M5 10a7 7 0 0 0 14 0"></path>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                  </svg>
                </button>

                <button type="submit" className="chat-send-btn" title="Send Message">
                  <span className="send-btn-text">{t('sendBtn')}</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                  </svg>
                </button>
              </form>
            </div>
          </>
        )}

        {/* Tab 2: Disease Predictors Hub */}
        {activeTab === 'predictor' && (
          <div className="chat-box" style={{ padding: '24px', display: 'block', overflowY: 'auto' }}>
            <DiseasePredictors 
              currentUser={currentUser}
              userEmail={currentUser?.email} 
              onPredictionCompleted={fetchHistory}
            />
          </div>
        )}

        {/* Tab 2.5: Geo-Localized Emergency Hospital & ICU Map */}
        {activeTab === 'hospitals' && (
          <div className="chat-box" style={{ padding: '24px', display: 'block', overflowY: 'auto' }}>
            <HospitalMap currentUser={currentUser} />
          </div>
        )}

        {/* Tab 2.6: Zero-Internet / Low-Bandwidth Offline Suite */}
        {activeTab === 'offline' && (
          <div className="chat-box" style={{ padding: '24px', display: 'block', overflowY: 'auto' }}>
            <OfflineEmergencySuite currentUser={currentUser} />
          </div>
        )}

        {/* Tab 3: Medical History */}
        {activeTab === 'history' && (
          <div className="chat-box" style={{ padding: '28px', display: 'block', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ color: '#063940', margin: 0 }}>Clinical Assessment History</h3>
                <p style={{ color: '#64748b', fontSize: '0.9rem', margin: '4px 0 0 0' }}>
                  Live records synced with SQLite database for <strong>{currentUser?.email}</strong>.
                </p>
              </div>
              <button 
                onClick={fetchHistory}
                style={{ padding: '8px 16px', background: '#063940', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.85rem' }}
              >
                Refresh Records
              </button>
            </div>

            {historyLoading && (
              <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                Loading your medical assessments...
              </div>
            )}

            {!historyLoading && historyRecords.length === 0 && (
              <div style={{ textAlign: 'center', padding: '60px', background: '#f8fafc', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
                <h4 style={{ color: '#063940', margin: '0 0 8px 0' }}>No Prior Clinical Assessments Found</h4>
                <p style={{ color: '#64748b', fontSize: '0.9rem', margin: '0 0 16px 0' }}>
                  Run your first AI disease evaluation (Cardiovascular, Liver, Kidney, Stroke, or PCOS) to see records here.
                </p>
                <button 
                  onClick={() => setActiveTab('predictor')}
                  className="submit-predictor-btn"
                  style={{ maxWidth: '240px', margin: '0 auto' }}
                >
                  Run Assessment Now
                </button>
              </div>
            )}

            {!historyLoading && historyRecords.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {historyRecords.map((rec) => (
                  <div key={rec.id} className="history-item-card" style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <strong style={{ color: '#063940', fontSize: '1rem', textTransform: 'capitalize' }}>
                          {rec.disease_type} Assessment
                        </strong>
                        <span style={{
                          background: rec.risk_level === 'High' ? '#fee2e2' : rec.risk_level === 'Moderate' ? '#fef3c7' : '#dcfce7',
                          color: rec.risk_level === 'High' ? '#b91c1c' : rec.risk_level === 'Moderate' ? '#b45309' : '#15803d',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 'bold'
                        }}>
                          {rec.risk_level} Risk ({rec.confidence_score}%)
                        </span>
                      </div>
                      <div style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '4px' }}>
                        Evaluated on: {rec.created_at || 'Recent'}
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.82rem', color: '#07A3B2', fontWeight: 600 }}>
                        {rec.recommended_doctor}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Health Reports & Analytics */}
        {activeTab === 'reports' && (
          <div className="chat-box" style={{ padding: '28px', display: 'block', overflowY: 'auto' }}>
            <h3 style={{ color: '#063940', marginBottom: '8px' }}>Comprehensive Health Analytics Report</h3>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '24px' }}>
              Aggregated longitudinal risk synthesis generated from your clinical assessments.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Total Assessments</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#063940', marginTop: '4px' }}>{totalAssessments}</div>
              </div>
              <div style={{ background: '#fef2f2', padding: '16px', borderRadius: '12px', border: '1px solid #fecaca' }}>
                <span style={{ fontSize: '0.8rem', color: '#991b1b', fontWeight: 600 }}>High Risk Alerts</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#dc2626', marginTop: '4px' }}>{highRiskCount}</div>
              </div>
              <div style={{ background: '#fffbeb', padding: '16px', borderRadius: '12px', border: '1px solid #fde68a' }}>
                <span style={{ fontSize: '0.8rem', color: '#92400e', fontWeight: 600 }}>Moderate Risk Flags</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#d97706', marginTop: '4px' }}>{moderateRiskCount}</div>
              </div>
              <div style={{ background: '#f0fdf4', padding: '16px', borderRadius: '12px', border: '1px solid #bbf7d0' }}>
                <span style={{ fontSize: '0.8rem', color: '#166534', fontWeight: 600 }}>Low Risk / Optimal</span>
                <div style={{ fontSize: '1.6rem', fontWeight: 'bold', color: '#16a34a', marginTop: '4px' }}>{lowRiskCount}</div>
              </div>
            </div>

            {/* Visual Risk Distribution */}
            <div style={{ background: 'white', padding: '20px', borderRadius: '12px', border: '1px solid #cbd5e1', marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '15px', color: '#063940' }}>Risk Severity Distribution Over All Records</h4>
              <div style={{ display: 'flex', alignItems: 'flex-end', height: '140px', gap: '30px', paddingBottom: '10px', borderBottom: '2px solid #cbd5e1' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                  <div style={{ height: `${totalAssessments > 0 ? (highRiskCount / totalAssessments) * 100 : 20}px`, width: '50px', background: '#ef4444', borderRadius: '6px 6px 0 0', minHeight: '10px' }} />
                  <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#b91c1c' }}>High ({highRiskCount})</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                  <div style={{ height: `${totalAssessments > 0 ? (moderateRiskCount / totalAssessments) * 100 : 20}px`, width: '50px', background: '#f59e0b', borderRadius: '6px 6px 0 0', minHeight: '10px' }} />
                  <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#b45309' }}>Moderate ({moderateRiskCount})</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                  <div style={{ height: `${totalAssessments > 0 ? ((lowRiskCount >= 0 ? lowRiskCount : 0) / totalAssessments) * 100 : 20}px`, width: '50px', background: '#10b981', borderRadius: '6px 6px 0 0', minHeight: '10px' }} />
                  <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#15803d' }}>Low ({lowRiskCount >= 0 ? lowRiskCount : 0})</span>
                </div>
              </div>
              <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '12px' }}>
                * AI risk scores dynamically derived from clinical biomarkers and SQLite telemetry.
              </p>
            </div>
          </div>
        )}

        {/* Tab 5: Settings & Profile */}
        {activeTab === 'settings' && (
          <div className="chat-box" style={{ padding: '24px', display: 'block', overflowY: 'auto' }}>
            
            {/* Header */}
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ color: '#063940', fontSize: '1.35rem', fontWeight: 800, margin: '0 0 4px 0' }}>
                Patient Settings & Medical Profile
              </h3>
              <p style={{ color: '#64748b', fontSize: '0.88rem', margin: 0 }}>
                Manage your saved clinical vitals, persistent 3-month authentication, and consultation preferences.
              </p>
            </div>

            {/* Success Banner */}
            {profileSaveSuccess && (
              <div style={{ background: '#dcfce7', border: '1px solid #22c55e', color: '#15803d', padding: '12px 18px', borderRadius: '12px', marginBottom: '20px', fontSize: '0.9rem', fontWeight: 700 }}>
                {profileSaveSuccess}
              </div>
            )}

            {/* Card 1: 3-Month Authentication & Session Security */}
            <div style={{
              background: 'linear-gradient(135deg, #063940 0%, #0c4a6e 100%)',
              color: 'white',
              borderRadius: '16px',
              padding: '20px 24px',
              marginBottom: '24px',
              boxShadow: '0 6px 20px rgba(6, 57, 64, 0.15)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ background: '#22c55e', color: 'white', padding: '2px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 900 }}>
                    ACTIVE SESSION
                  </span>
                  <span style={{ fontSize: '0.85rem', opacity: 0.9 }}>
                    3-Month Extended Authentication
                  </span>
                </div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '1.2rem', fontWeight: 800 }}>
                  {currentUser?.name || currentUser?.fullName || currentUser?.email}
                </h4>
                <div style={{ fontSize: '0.82rem', opacity: 0.85 }}>
                  Account: <strong>{currentUser?.email}</strong> • Valid until: <strong>{sessionExpiryDate || '90 Days Active'}</strong>
                </div>
                <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', opacity: 0.8 }}>
                  You will stay securely signed in on this device for 3 months without having to re-enter your login credentials.
                </p>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                style={{
                  background: 'rgba(255,255,255,0.15)',
                  color: 'white',
                  border: '1px solid rgba(255,255,255,0.3)',
                  borderRadius: '10px',
                  padding: '10px 18px',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Sign Out
              </button>
            </div>

            {/* Card 2: Patient Clinical Vitals & Auto-Fill Profile Form */}
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '24px', marginBottom: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.04)' }}>
              <div style={{ marginBottom: '18px' }}>
                <h4 style={{ color: '#063940', fontSize: '1.1rem', fontWeight: 800, margin: '0 0 4px 0' }}>
                  Saved Patient Vitals (Auto-Filled in All Predictors)
                </h4>
                <p style={{ color: '#64748b', fontSize: '0.84rem', margin: 0 }}>
                  Save your baseline details once. All disease evaluations, BMI calculators, and emergency passes will auto-populate automatically.
                </p>
              </div>

              <form onSubmit={handleSaveProfile} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
                <div>
                  <label className="field-label">Full Name</label>
                  <input
                    type="text"
                    className="form-input"
                    value={profileFormData.name}
                    onChange={(e) => setProfileFormData({...profileFormData, name: e.target.value})}
                    placeholder="Enter full name"
                    required
                  />
                </div>

                <div>
                  <label className="field-label">Age (Years)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={profileFormData.age}
                    onChange={(e) => setProfileFormData({...profileFormData, age: e.target.value})}
                    placeholder="e.g. 32"
                    required
                  />
                </div>

                <div>
                  <label className="field-label">Gender</label>
                  <select
                    className="form-input"
                    value={profileFormData.gender}
                    onChange={(e) => setProfileFormData({...profileFormData, gender: e.target.value})}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="field-label">Blood Group</label>
                  <select
                    className="form-input"
                    value={profileFormData.bloodGroup}
                    onChange={(e) => setProfileFormData({...profileFormData, bloodGroup: e.target.value})}
                  >
                    <option value="A+ve">A+ve</option>
                    <option value="A-ve">A-ve</option>
                    <option value="B+ve">B+ve</option>
                    <option value="B-ve">B-ve</option>
                    <option value="O+ve">O+ve</option>
                    <option value="O-ve">O-ve</option>
                    <option value="AB+ve">AB+ve</option>
                    <option value="AB-ve">AB-ve</option>
                  </select>
                </div>

                <div>
                  <label className="field-label">Height (cm)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={profileFormData.height}
                    onChange={(e) => setProfileFormData({...profileFormData, height: e.target.value})}
                    placeholder="e.g. 172"
                  />
                </div>

                <div>
                  <label className="field-label">Weight (kg)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={profileFormData.weight}
                    onChange={(e) => setProfileFormData({...profileFormData, weight: e.target.value})}
                    placeholder="e.g. 68"
                  />
                </div>

                <div>
                  <label className="field-label">Resting Blood Pressure (mm Hg)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={profileFormData.trestbps}
                    onChange={(e) => setProfileFormData({...profileFormData, trestbps: e.target.value})}
                    placeholder="e.g. 120"
                  />
                </div>

                <div>
                  <label className="field-label">Phone Number</label>
                  <input
                    type="tel"
                    className="form-input"
                    value={profileFormData.phone}
                    onChange={(e) => setProfileFormData({...profileFormData, phone: e.target.value})}
                    placeholder="+91 98765 43210"
                  />
                </div>

                <div style={{ gridColumn: '1 / -1' }}>
                  <label className="field-label">Known Allergies</label>
                  <input
                    type="text"
                    className="form-input"
                    value={profileFormData.allergies}
                    onChange={(e) => setProfileFormData({...profileFormData, allergies: e.target.value})}
                    placeholder="e.g. Penicillin, Peanuts, Sulfa (or 'None')"
                  />
                </div>

                <div style={{ gridColumn: '1 / -1' }}>
                  <label className="field-label">Chronic Medical Conditions</label>
                  <input
                    type="text"
                    className="form-input"
                    value={profileFormData.chronicConditions}
                    onChange={(e) => setProfileFormData({...profileFormData, chronicConditions: e.target.value})}
                    placeholder="e.g. Type 2 Diabetes, Mild Hypertension (or 'None')"
                  />
                </div>

                <div style={{ gridColumn: '1 / -1', marginTop: '6px' }}>
                  <button
                    type="submit"
                    className="submit-predictor-btn"
                    style={{ maxWidth: '320px' }}
                  >
                    Save Medical Profile & Auto-Fill
                  </button>
                </div>
              </form>
            </div>

            {/* Card 3: Consultation & Language Preferences */}
            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.04)' }}>
              <h4 style={{ color: '#063940', fontSize: '1.1rem', fontWeight: 800, margin: '0 0 16px 0' }}>
                Consultation & Language Preferences
              </h4>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
                <div>
                  <label className="field-label">Interface & Voice Language</label>
                  <div className="lang-selector-group" style={{ display: 'inline-flex', marginTop: '6px' }}>
                    <button
                      type="button"
                      className={`lang-pill-btn ${i18n.language === 'en' ? 'active' : ''}`}
                      onClick={() => i18n.changeLanguage('en')}
                    >
                      English (EN)
                    </button>
                    <button
                      type="button"
                      className={`lang-pill-btn ${i18n.language === 'te' ? 'active' : ''}`}
                      onClick={() => i18n.changeLanguage('te')}
                    >
                      తెలుగు (Telugu)
                    </button>
                    <button
                      type="button"
                      className={`lang-pill-btn ${i18n.language === 'hi' ? 'active' : ''}`}
                      onClick={() => i18n.changeLanguage('hi')}
                    >
                      हिंदी (Hindi)
                    </button>
                  </div>
                </div>

                <div>
                  <label className="field-label">Local Data Cache</label>
                  <button
                    type="button"
                    onClick={() => {
                      localStorage.removeItem('quantum_offline_medical_id');
                      alert("Local emergency pass cache refreshed.");
                    }}
                    style={{
                      marginTop: '6px',
                      padding: '10px 18px',
                      borderRadius: '10px',
                      border: '1px solid #cbd5e1',
                      background: '#f8fafc',
                      color: '#475569',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      cursor: 'pointer'
                    }}
                  >
                    Refresh Emergency Cache
                  </button>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* Mobile Bottom Navigation Bar (< 768px) */}

        <nav className="mobile-bottom-nav">
          <button 
            type="button" 
            className={`mobile-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => { setActiveTab('chat'); setSidebarOpen(false); }}
          >
            <span className="mobile-nav-icon">💬</span>
            <span className="mobile-nav-label">{t('navChat') || 'Chat'}</span>
          </button>
          <button 
            type="button" 
            className={`mobile-nav-item ${activeTab === 'predictor' ? 'active' : ''}`}
            onClick={() => { setActiveTab('predictor'); setSidebarOpen(false); }}
          >
            <span className="mobile-nav-icon">🩺</span>
            <span className="mobile-nav-label">{t('navPredictors') || 'Predictors'}</span>
          </button>
          <button 
            type="button" 
            className={`mobile-nav-item ${activeTab === 'hospitals' ? 'active' : ''}`}
            onClick={() => { setActiveTab('hospitals'); setSidebarOpen(false); }}
          >
            <span className="mobile-nav-icon">🏥</span>
            <span className="mobile-nav-label">{t('navHospitals') || 'Hospitals'}</span>
          </button>
          <button 
            type="button" 
            className={`mobile-nav-item ${activeTab === 'offline' ? 'active' : ''}`}
            onClick={() => { setActiveTab('offline'); setSidebarOpen(false); }}
          >
            <span className="mobile-nav-icon">📶</span>
            <span className="mobile-nav-label">Offline</span>
          </button>
          <button 
            type="button" 
            className={`mobile-nav-item ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => { setActiveTab('history'); setSidebarOpen(false); }}
          >
            <span className="mobile-nav-icon">📋</span>
            <span className="mobile-nav-label">{t('navHistory') || 'History'}</span>
          </button>
        </nav>


      </main>


      {/* Emergency Modal */}
      <EmergencyAssistant
        open={emergencyModalOpen}
        onClose={() => setEmergencyModalOpen(false)}
        userEmail={currentUser?.email}
      />

      {/* Add Person Modal */}
      {showAddPersonModal && (
        <div style={{ position: 'fixed', inset: '0', background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ background: 'white', padding: '30px', borderRadius: '12px', width: '380px', boxShadow: '0 10px 25px rgba(0,0,0,0.2)' }}>
            <h3 style={{ color: '#063940', marginBottom: '20px' }}>Add Family Member</h3>
            <form onSubmit={handleAddPersonSubmit}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '0.9rem' }}>{t('fullName')}</label>
                <input 
                  type="text" 
                  placeholder="Enter member's full name"
                  value={newPerson.name} 
                  onChange={(e) => setNewPerson({ ...newPerson, name: e.target.value })}
                  required
                  className="form-input"
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '0.9rem' }}>{t('age')}</label>
                <input 
                  type="number" 
                  placeholder="Enter age (e.g. 30)"
                  value={newPerson.age} 
                  onChange={(e) => setNewPerson({ ...newPerson, age: e.target.value })}
                  required
                  className="form-input"
                />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '0.9rem' }}>{t('gender')}</label>
                <select 
                  value={newPerson.gender} 
                  onChange={(e) => setNewPerson({ ...newPerson, gender: e.target.value })}
                  required
                  className="form-input"
                >
                  <option value="">Select Gender</option>
                  <option value="Male">{t('male')}</option>
                  <option value="Female">{t('female')}</option>
                  <option value="Other">{t('other')}</option>
                </select>

              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button type="submit" style={{ flex: 1, padding: '10px', background: '#063940', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Add Member</button>
                <button type="button" onClick={() => setShowAddPersonModal(false)} style={{ flex: 1, padding: '10px', background: '#cbd5e1', color: '#333', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default HomePage;