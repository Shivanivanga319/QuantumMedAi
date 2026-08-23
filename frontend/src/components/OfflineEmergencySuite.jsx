import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

export default function OfflineEmergencySuite({ currentUser }) {
  const { t, i18n } = useTranslation();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [simulatedOffline, setSimulatedOffline] = useState(false);
  const [activeOfflineTab, setActiveOfflineTab] = useState('cpr'); // 'cpr', 'firstaid', 'sos', 'medical_id', 'hospitals'
  const [selectedFirstAid, setSelectedFirstAid] = useState('choking'); // 'choking', 'bleeding', 'stroke', 'seizure', 'snakebite', 'burns'
  
  // CPR Metronome State
  const [cprActive, setCprActive] = useState(false);
  const [cprCount, setCprCount] = useState(0);
  const [cprElapsedSeconds, setCprElapsedSeconds] = useState(0);
  const audioCtxRef = useRef(null);
  const metronomeIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);

  // Offline GPS Coordinates
  const [offlineGps, setOfflineGps] = useState({ lat: 17.4258, lng: 78.4116, accuracy: 15 });
  const [gpsStatus, setGpsStatus] = useState('Cached GPS: Ready');
  const [smsCopied, setSmsCopied] = useState(false);

  // Offline Medical ID State (Cached in LocalStorage)
  const [medicalId, setMedicalId] = useState(() => {
    const cached = localStorage.getItem('quantum_offline_medical_id');
    if (cached) {
      try { return JSON.parse(cached); } catch (e) {}
    }
    return {
      fullName: currentUser?.fullName || currentUser?.name || 'Patient',
      bloodGroup: 'O+ve',
      age: '32',
      allergies: 'Penicillin, Sulfa drugs',
      chronicConditions: 'Hypertension, Mild Asthma',
      emergencyContactName: 'Primary Guardian',
      emergencyContactPhone: '+91 98765 43210',
      organDonor: 'Yes'
    };
  });
  const [editingMedicalId, setEditingMedicalId] = useState(false);

  // Online / Offline event listeners
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Acquire offline GPS coordinate via hardware satellite
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setOfflineGps({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: Math.round(pos.coords.accuracy || 10)
          });
          setGpsStatus(`Satellite GPS Locked: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)} (±${Math.round(pos.coords.accuracy)}m)`);
        },
        () => {
          setGpsStatus('Using Cached Regional GPS Coordinates');
        },
        { enableHighAccuracy: true, timeout: 6000 }
      );
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      stopCprMetronome();
    };
  }, []);

  // Save Medical ID to LocalStorage
  const handleSaveMedicalId = (e) => {
    e.preventDefault();
    localStorage.setItem('quantum_offline_medical_id', JSON.stringify(medicalId));
    setEditingMedicalId(false);
  };

  // CPR Metronome Audio Synthesizer (110 BPM = 545.45 ms interval)
  const playMetronomeBeep = () => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume();
      }
      const osc = audioCtxRef.current.createOscillator();
      const gain = audioCtxRef.current.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtxRef.current.currentTime); // High clear beep (880Hz A5)
      gain.gain.setValueAtTime(0.3, audioCtxRef.current.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtxRef.current.currentTime + 0.08);
      osc.connect(gain);
      gain.connect(audioCtxRef.current.destination);
      osc.start();
      osc.stop(audioCtxRef.current.currentTime + 0.09);
    } catch (e) {
      console.warn("AudioContext not permitted yet:", e);
    }
  };

  const startCprMetronome = () => {
    setCprActive(true);
    setCprCount(0);
    setCprElapsedSeconds(0);

    playMetronomeBeep();
    setCprCount(1);

    // 110 BPM metronome interval
    metronomeIntervalRef.current = setInterval(() => {
      playMetronomeBeep();
      setCprCount(prev => prev + 1);
    }, 545.45);

    timerIntervalRef.current = setInterval(() => {
      setCprElapsedSeconds(prev => prev + 1);
    }, 1000);
  };

  const stopCprMetronome = () => {
    setCprActive(false);
    if (metronomeIntervalRef.current) clearInterval(metronomeIntervalRef.current);
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
  };

  // Generate Offline SOS Payload
  const mapsLink = `https://maps.google.com/?q=${offlineGps.lat},${offlineGps.lng}`;
  const sosSmsText = `[OFFLINE SOS ALERT - NO INTERNET]\nPatient: ${medicalId.fullName} (Blood: ${medicalId.bloodGroup}, Age: ${medicalId.age})\nEmergency: Acute Medical Distress / Trauma\nGPS Location: ${offlineGps.lat.toFixed(5)}, ${offlineGps.lng.toFixed(5)}\nGoogle Maps Pin: ${mapsLink}\nAllergies: ${medicalId.allergies}\nGuardian: ${medicalId.emergencyContactPhone}\nDispatched via QuantumMedAI Offline Protocol. Call 108 immediately.`;
  const smsHref = `sms:108?body=${encodeURIComponent(sosSmsText)}`;
  const waHref = `https://wa.me/?text=${encodeURIComponent(sosSmsText)}`;

  const copySosText = () => {
    navigator.clipboard.writeText(sosSmsText);
    setSmsCopied(true);
    setTimeout(() => setSmsCopied(false), 2500);
  };

  // Offline Hospital Directory (Cached locally)
  const offlineHospitals = [
    { name: "Apollo Emergency Center", city: "Hyderabad", phone: "1066", direct: "+91 40 2360 7777", addr: "Jubilee Hills, Road No. 72", icu: "Level 1 Trauma & Cardiac ICU" },
    { name: "NIMS Apex Govt Hospital", city: "Hyderabad", phone: "108", direct: "+91 40 2348 9000", addr: "Punjagutta, Hyderabad", icu: "Govt Free ICU & Snakebite Center" },
    { name: "Care Multi-Specialty Hospital", city: "Hyderabad", phone: "+91 40 3041 8888", direct: "+91 40 6165 6565", addr: "Banjara Hills, Road No. 1", icu: "Cardiac & Stroke Emergency" },
    { name: "Yashoda Trauma Center", city: "Hyderabad", phone: "105910", direct: "+91 40 4567 4567", addr: "Somajiguda, Raj Bhavan Rd", icu: "Comprehensive Neuro ICU" },
    { name: "AIIMS National Trauma Center", city: "New Delhi", phone: "108", direct: "+91 11 2658 8500", addr: "Ansari Nagar, New Delhi", icu: "National Apex ICU & Poison Center" },
    { name: "Manipal Hospital Emergency", city: "Bengaluru", phone: "1059", direct: "+91 80 2502 4444", addr: "HAL Airport Road, Bangalore", icu: "Cardiac & Stroke Thrombolysis" }
  ];

  const effectivelyOffline = !isOnline || simulatedOffline;

  return (
    <div className="offline-suite-container" style={{ padding: '4px' }}>
      
      {/* Network Status Header & Test Simulation Switch */}
      <div style={{
        background: effectivelyOffline ? 'linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%)' : 'linear-gradient(135deg, #063940 0%, #0c4a6e 100%)',
        color: 'white',
        borderRadius: '16px',
        padding: '18px 22px',
        marginBottom: '20px',
        boxShadow: '0 6px 20px rgba(0,0,0,0.15)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '14px',
            height: '14px',
            borderRadius: '50%',
            background: effectivelyOffline ? '#ef4444' : '#22c55e',
            boxShadow: effectivelyOffline ? '0 0 10px #ef4444' : '0 0 10px #22c55e'
          }} />
          <div>
            <h2 style={{ margin: '0 0 4px 0', fontSize: '1.25rem', fontWeight: 800 }}>
              {effectivelyOffline ? 'Offline Emergency Mode (Zero-Internet Active)' : 'Zero-Internet & Low-Bandwidth Medical Suite'}
            </h2>
            <p style={{ margin: 0, fontSize: '0.85rem', opacity: 0.9 }}>
              {effectivelyOffline 
                ? 'All CPR guidance, triage algorithms, cellular SMS SOS, and Medical ID operate 100% locally on your device.'
                : 'Operates continuously without Wi-Fi or Mobile Data via cached device storage and cellular hardware.'}
            </p>
          </div>
        </div>

        <button
          onClick={() => setSimulatedOffline(!simulatedOffline)}
          style={{
            background: effectivelyOffline ? '#22c55e' : '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            padding: '8px 16px',
            fontWeight: 700,
            fontSize: '0.82rem',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
          }}
        >
          {simulatedOffline ? 'Exit Offline Simulation' : 'Simulate Zero Internet'}
        </button>
      </div>

      {/* Main Feature Tabs */}
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '20px' }}>
        <button
          onClick={() => setActiveOfflineTab('cpr')}
          className={`lang-pill-btn ${activeOfflineTab === 'cpr' ? 'active' : ''}`}
          style={{ padding: '10px 18px', fontSize: '0.88rem', fontWeight: 800, borderRadius: '12px', border: '1px solid #cbd5e1' }}
        >
          CPR Metronome
        </button>
        <button
          onClick={() => setActiveOfflineTab('firstaid')}
          className={`lang-pill-btn ${activeOfflineTab === 'firstaid' ? 'active' : ''}`}
          style={{ padding: '10px 18px', fontSize: '0.88rem', fontWeight: 800, borderRadius: '12px', border: '1px solid #cbd5e1' }}
        >
          First-Aid Guides
        </button>
        <button
          onClick={() => setActiveOfflineTab('sos')}
          className={`lang-pill-btn ${activeOfflineTab === 'sos' ? 'active' : ''}`}
          style={{ padding: '10px 18px', fontSize: '0.88rem', fontWeight: 800, borderRadius: '12px', border: '1px solid #cbd5e1' }}
        >
          Cellular SMS & Call Hub
        </button>
        <button
          onClick={() => setActiveOfflineTab('medical_id')}
          className={`lang-pill-btn ${activeOfflineTab === 'medical_id' ? 'active' : ''}`}
          style={{ padding: '10px 18px', fontSize: '0.88rem', fontWeight: 800, borderRadius: '12px', border: '1px solid #cbd5e1' }}
        >
          Offline Medical ID Pass
        </button>
        <button
          onClick={() => setActiveOfflineTab('hospitals')}
          className={`lang-pill-btn ${activeOfflineTab === 'hospitals' ? 'active' : ''}`}
          style={{ padding: '10px 18px', fontSize: '0.88rem', fontWeight: 800, borderRadius: '12px', border: '1px solid #cbd5e1' }}
        >
          Offline Hospital Numbers
        </button>
      </div>

      {/* TAB 1: CPR METRONOME ASSISTANT */}
      {activeOfflineTab === 'cpr' && (
        <div style={{ background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.05)' }}>
          <div style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto' }}>
            <h3 style={{ color: '#991b1b', fontSize: '1.4rem', fontWeight: 900, margin: '0 0 6px 0' }}>
              CPR Resuscitation Metronome (110 BPM)
            </h3>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '24px' }}>
              Push hard and fast in the center of the chest to the beat. AHA Standard: 100–120 compressions per minute, 5–6 cm depth.
            </p>

            {/* Pulsing Visual Rhythm Ring */}
            <div style={{
              width: '180px',
              height: '180px',
              borderRadius: '50%',
              margin: '0 auto 24px auto',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: cprActive ? (cprCount % 2 === 0 ? '#fee2e2' : '#fecaca') : '#f1f5f9',
              border: cprActive ? '6px solid #dc2626' : '6px solid #cbd5e1',
              boxShadow: cprActive ? '0 0 30px rgba(220, 38, 38, 0.4)' : 'none',
              transition: 'all 0.1s ease',
              transform: cprActive && cprCount % 2 === 0 ? 'scale(1.06)' : 'scale(1)'
            }}>
              <span style={{ fontSize: '2.4rem', fontWeight: 900, color: cprActive ? '#991b1b' : '#64748b' }}>
                {cprCount}
              </span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#64748b' }}>
                {cprActive ? 'PRESS NOW' : 'STANDBY'}
              </span>
            </div>

            {/* CPR Controls */}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginBottom: '24px' }}>
              {!cprActive ? (
                <button
                  onClick={startCprMetronome}
                  style={{
                    background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
                    color: 'white',
                    padding: '14px 32px',
                    borderRadius: '30px',
                    border: 'none',
                    fontWeight: 900,
                    fontSize: '1.1rem',
                    cursor: 'pointer',
                    boxShadow: '0 4px 16px rgba(220, 38, 38, 0.35)'
                  }}
                >
                  Start CPR Metronome Beat
                </button>
              ) : (
                <button
                  onClick={stopCprMetronome}
                  style={{
                    background: '#334155',
                    color: 'white',
                    padding: '14px 32px',
                    borderRadius: '30px',
                    border: 'none',
                    fontWeight: 900,
                    fontSize: '1.1rem',
                    cursor: 'pointer'
                  }}
                >
                  Stop Metronome
                </button>
              )}
            </div>

            {/* CPR Live Resuscitation Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', background: '#f8fafc', padding: '14px', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '24px' }}>
              <div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 700 }}>Total Compressions</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#063940' }}>{cprCount}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 700 }}>Target Ratio</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#07A3B2' }}>30 : 2 Breaths</div>
              </div>
              <div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', fontWeight: 700 }}>Resuscitation Time</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#991b1b' }}>
                  {Math.floor(cprElapsedSeconds / 60)}:{(cprElapsedSeconds % 60).toString().padStart(2, '0')}
                </div>
              </div>
            </div>

            {/* Clinical CPR Action Checklist */}
            <div style={{ textAlign: 'left', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '12px', padding: '16px' }}>
              <strong style={{ color: '#991b1b', display: 'block', marginBottom: '8px' }}>Essential CPR Steps:</strong>
              <ol style={{ margin: 0, paddingLeft: '20px', color: '#7f1d1d', fontSize: '0.88rem', lineHeight: '1.6' }}>
                <li><strong>Check Responsiveness:</strong> Tap shoulder and shout "Are you okay?". If no response, tell someone to call 108.</li>
                <li><strong>Hand Placement:</strong> Place heel of one hand in center of chest (lower half of sternum), interlock second hand on top.</li>
                <li><strong>Compression Technique:</strong> Keep arms straight, lock elbows, push straight down at least 5 cm (2 inches). Allow complete chest recoil.</li>
                <li><strong>Rescue Breaths:</strong> If trained, give 2 rescue breaths every 30 compressions. If untrained, provide continuous Hands-Only CPR.</li>
              </ol>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: CLINICAL FIRST-AID PROTOCOLS */}
      {activeOfflineTab === 'firstaid' && (
        <div style={{ background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '20px', borderBottom: '1px solid #e2e8f0' }}>
            {[
              { id: 'choking', label: 'Choking / Heimlich' },
              { id: 'bleeding', label: 'Severe Bleeding & Tourniquet' },
              { id: 'stroke', label: 'Acute Stroke (FAST)' },
              { id: 'seizure', label: 'Seizures & Airway' },
              { id: 'snakebite', label: 'Snakebite & Poisoning' },
              { id: 'burns', label: 'Burns & Scalds' }
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setSelectedFirstAid(item.id)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '10px',
                  border: selectedFirstAid === item.id ? '2px solid #063940' : '1px solid #cbd5e1',
                  background: selectedFirstAid === item.id ? '#063940' : '#f8fafc',
                  color: selectedFirstAid === item.id ? 'white' : '#334155',
                  fontWeight: 700,
                  fontSize: '0.84rem',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Guide Content */}
          {selectedFirstAid === 'choking' && (
            <div>
              <h3 style={{ color: '#063940', margin: '0 0 10px 0' }}>Choking Management: Heimlich Maneuver</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <strong style={{ color: '#063940', display: 'block', marginBottom: '8px' }}>For Conscious Adults & Children (&gt; 1 yr):</strong>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.88rem', color: '#475569', lineHeight: '1.6' }}>
                    <li><strong>5 Back Blows:</strong> Stand behind, lean victim forward, deliver 5 firm heel-of-hand blows between shoulder blades.</li>
                    <li><strong>5 Abdominal Thrusts:</strong> Make a fist above navel, grasp with other hand, deliver 5 inward and upward thrusts.</li>
                    <li>Repeat 5 blows & 5 thrusts until airway clears or person becomes unconscious.</li>
                  </ul>
                </div>
                <div style={{ background: '#fef2f2', padding: '16px', borderRadius: '12px', border: '1px solid #fecaca' }}>
                  <strong style={{ color: '#991b1b', display: 'block', marginBottom: '8px' }}>For Infants (&lt; 1 yr):</strong>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.88rem', color: '#7f1d1d', lineHeight: '1.6' }}>
                    <li>Lay infant face down along your forearm, head lower than chest.</li>
                    <li>Deliver 5 gentle back blows with heel of hand.</li>
                    <li>Turn face up, deliver 5 chest thrusts with 2 fingers in center of sternum.</li>
                    <li><strong>NEVER</strong> perform blind finger sweeps in infant mouths.</li>
                  </ul>
                </div>

              </div>
            </div>
          )}

          {selectedFirstAid === 'bleeding' && (
            <div>
              <h3 style={{ color: '#991b1b', margin: '0 0 10px 0' }}>Severe Hemorrhage & Bleeding Control</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', borderLeft: '4px solid #dc2626' }}>
                  <strong style={{ color: '#063940' }}>Step 1: Direct Firm Pressure</strong>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#475569' }}>
                    Apply immediate direct pressure on wound using a sterile gauze or clean cloth. Maintain continuous uninterrupted pressure for at least 5 minutes without lifting the cloth.
                  </p>
                </div>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', borderLeft: '4px solid #dc2626' }}>
                  <strong style={{ color: '#063940' }}>Step 2: Elevation & Pressure Bandage</strong>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#475569' }}>
                    Elevate bleeding limb above heart level if no fracture is suspected. Secure dressing firmly with a snug bandage.
                  </p>
                </div>
                <div style={{ background: '#fef2f2', padding: '16px', borderRadius: '12px', borderLeft: '4px solid #991b1b' }}>
                  <strong style={{ color: '#991b1b' }}>Step 3: Tourniquet Application (For Life-Threatening Limb Arterial Bleeding)</strong>
                  <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#7f1d1d' }}>
                    Place tourniquet 2–3 inches above wound (closer to torso, NEVER over a joint). Tighten until bright red pulsing bleeding completely stops. Record exact application time on victim's forehead.
                  </p>
                </div>
              </div>
            </div>
          )}

          {selectedFirstAid === 'stroke' && (
            <div>
              <h3 style={{ color: '#063940', margin: '0 0 10px 0' }}>Acute Stroke Assessment: F.A.S.T. Protocol</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                <div style={{ background: '#f0fdfa', border: '1px solid #ccfbf1', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#0f766e', display: 'block', fontSize: '1.1rem' }}>F - Face</strong>
                  <span style={{ fontSize: '0.86rem', color: '#134e4a' }}>Ask the person to smile. Does one side of the face droop?</span>
                </div>
                <div style={{ background: '#f0fdfa', border: '1px solid #ccfbf1', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#0f766e', display: 'block', fontSize: '1.1rem' }}>A - Arms</strong>
                  <span style={{ fontSize: '0.86rem', color: '#134e4a' }}>Ask person to raise both arms. Does one arm drift downward?</span>
                </div>
                <div style={{ background: '#f0fdfa', border: '1px solid #ccfbf1', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#0f766e', display: 'block', fontSize: '1.1rem' }}>S - Speech</strong>
                  <span style={{ fontSize: '0.86rem', color: '#134e4a' }}>Ask person to repeat a simple sentence. Is speech slurred or strange?</span>
                </div>
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#991b1b', display: 'block', fontSize: '1.1rem' }}>T - Time</strong>
                  <span style={{ fontSize: '0.86rem', color: '#7f1d1d' }}>If any symptom present, call 108 immediately. Note the exact time symptoms started.</span>
                </div>
              </div>
              <p style={{ fontSize: '0.85rem', color: '#64748b', margin: 0 }}>
                Thrombolytic clot-busting medication (tPA) is most effective when administered within 3 to 4.5 hours of symptom onset.
              </p>
            </div>
          )}

          {selectedFirstAid === 'seizure' && (
            <div>
              <h3 style={{ color: '#063940', margin: '0 0 10px 0' }}>Seizure & Convulsion First-Aid</h3>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.88rem', color: '#334155', lineHeight: '1.7' }}>
                <li><strong>Clear Hazards:</strong> Move hard, sharp, or hot objects away from the person.</li>
                <li><strong>Cushion Head:</strong> Place something soft under their head (folded jacket or pillow).</li>
                <li><strong>Turn on Side:</strong> Gently roll person onto their side (recovery position) to keep airway clear.</li>
                <li><strong>DO NOT Restrain:</strong> Do not hold the person down or attempt to stop their body jerking.</li>
                <li><strong>DO NOT Put Anything in Mouth:</strong> No spoons, keys, fingers, or water. Teeth clenching will not cause swallowing of tongue.</li>
                <li><strong>Time the Seizure:</strong> If seizure lasts longer than 5 minutes or repeats without waking, call 108 immediately.</li>
              </ul>
            </div>
          )}

          {selectedFirstAid === 'snakebite' && (
            <div>
              <h3 style={{ color: '#991b1b', margin: '0 0 10px 0' }}>Venomous Snakebite Protocol</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#166534', display: 'block', marginBottom: '6px' }}>DO:</strong>
                  <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.85rem', color: '#14532d', lineHeight: '1.6' }}>
                    <li>Keep patient completely calm and still. Movement accelerates venom absorption.</li>
                    <li>Immobilize the bitten limb with a splint below heart level.</li>
                    <li>Remove rings, watches, and tight clothing before swelling begins.</li>
                    <li>Transport immediately to nearest anti-venom hospital.</li>
                  </ul>
                </div>
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '14px', borderRadius: '10px' }}>
                  <strong style={{ color: '#991b1b', display: 'block', marginBottom: '6px' }}>DO NOT:</strong>
                  <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.85rem', color: '#7f1d1d', lineHeight: '1.6' }}>
                    <li><strong>DO NOT</strong> cut the wound or attempt to suck venom.</li>
                    <li><strong>DO NOT</strong> apply ice, electricity, or herbal paste.</li>
                    <li><strong>DO NOT</strong> apply tight arterial tourniquets (causes severe tissue necrosis).</li>
                    <li><strong>DO NOT</strong> give alcohol or caffeinated beverages.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {selectedFirstAid === 'burns' && (
            <div>
              <h3 style={{ color: '#063940', margin: '0 0 10px 0' }}>Thermal & Chemical Burns Protocol</h3>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.88rem', color: '#334155', lineHeight: '1.7' }}>
                <li><strong>Cool Immediately:</strong> Hold burned area under cool running tap water for 10 to 20 minutes. (Do NOT use ice).</li>
                <li><strong>Remove Tight Items:</strong> Gently take off rings or constricting clothing before swelling occurs.</li>
                <li><strong>Cover Loosely:</strong> Cover with a clean, dry, non-stick sterile dressing or clean plastic cling film.</li>
                <li><strong>DO NOT Break Blisters:</strong> Intact skin protects against severe infection.</li>
                <li><strong>DO NOT Apply Butter or Ointments:</strong> Traps heat in tissue. Seek medical attention for burns larger than palm size.</li>
              </ul>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CELLULAR HARDWARE SMS & DIRECT CALLING HUB */}
      {activeOfflineTab === 'sos' && (
        <div style={{ background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.05)' }}>
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ color: '#063940', fontSize: '1.25rem', fontWeight: 800, margin: '0 0 4px 0' }}>
              Cellular Hardware Emergency SOS Hub (Zero Data Required)
            </h3>
            <p style={{ color: '#64748b', fontSize: '0.88rem', margin: 0 }}>
              Dispatches emergency telemetry through native hardware GSM cellular SMS without internet.
            </p>
          </div>

          {/* Quick Dial Matrix */}
          <div style={{ marginBottom: '24px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#64748b', display: 'block', marginBottom: '10px' }}>
              DIRECT 1-TAP EMERGENCY CALL HOTLINES
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
              <a
                href="tel:108"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#dc2626',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '14px',
                  borderRadius: '12px',
                  fontWeight: 800,
                  fontSize: '0.95rem',
                  boxShadow: '0 4px 12px rgba(220, 38, 38, 0.25)'
                }}
              >
                Call 108 (Ambulance)
              </a>
              <a
                href="tel:112"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#0f766e',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '14px',
                  borderRadius: '12px',
                  fontWeight: 800,
                  fontSize: '0.95rem'
                }}
              >
                Call 112 (National All-Emergency)
              </a>
              <a
                href="tel:102"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#0284c7',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '14px',
                  borderRadius: '12px',
                  fontWeight: 800,
                  fontSize: '0.95rem'
                }}
              >
                Call 102 (Maternity / Infant)
              </a>
              <a
                href="tel:104"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#475569',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '14px',
                  borderRadius: '12px',
                  fontWeight: 800,
                  fontSize: '0.95rem'
                }}
              >
                Call 104 (Health Advice)
              </a>
            </div>
          </div>

          {/* SMS Dispatch Actions */}
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '14px', padding: '18px', marginBottom: '20px' }}>
            <strong style={{ color: '#991b1b', fontSize: '1rem', display: 'block', marginBottom: '6px' }}>
              Automated Cellular SMS SOS Payload
            </strong>
            <p style={{ color: '#7f1d1d', fontSize: '0.84rem', margin: '0 0 12px 0' }}>
              Includes patient name, blood group, exact satellite GPS coordinates, and direct Google Maps navigation link.
            </p>

            <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px', fontFamily: 'monospace', fontSize: '0.8rem', color: '#334155', whiteSpace: 'pre-wrap', marginBottom: '14px' }}>
              {sosSmsText}
            </div>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <a
                href={smsHref}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#dc2626',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontWeight: 800,
                  fontSize: '0.9rem'
                }}
              >
                Send Cellular SMS to 108
              </a>
              <a
                href={waHref}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#16a34a',
                  color: 'white',
                  textDecoration: 'none',
                  padding: '12px 20px',
                  borderRadius: '10px',
                  fontWeight: 800,
                  fontSize: '0.9rem'
                }}
              >
                Send WhatsApp SOS
              </a>
              <button
                onClick={copySosText}
                style={{
                  padding: '12px 18px',
                  borderRadius: '10px',
                  border: '1px solid #cbd5e1',
                  background: 'white',
                  color: '#334155',
                  fontWeight: 700,
                  fontSize: '0.88rem',
                  cursor: 'pointer'
                }}
              >
                {smsCopied ? 'SOS Text Copied' : 'Copy SOS Text'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: OFFLINE EMERGENCY MEDICAL ID PASS */}
      {activeOfflineTab === 'medical_id' && (
        <div style={{ background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h3 style={{ color: '#063940', fontSize: '1.25rem', fontWeight: 800, margin: '0 0 4px 0' }}>
                Offline Emergency Medical ID & QR Pass
              </h3>
              <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
                First responders & paramedics can read your vital conditions & emergency contacts offline.
              </p>
            </div>
            <button
              onClick={() => setEditingMedicalId(!editingMedicalId)}
              style={{
                background: editingMedicalId ? '#334155' : '#07A3B2',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 14px',
                fontWeight: 700,
                fontSize: '0.82rem',
                cursor: 'pointer'
              }}
            >
              {editingMedicalId ? 'Cancel' : 'Edit Medical ID'}
            </button>
          </div>

          {editingMedicalId ? (
            <form onSubmit={handleSaveMedicalId} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label className="field-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={medicalId.fullName}
                  onChange={e => setMedicalId({...medicalId, fullName: e.target.value})}
                  required
                />
              </div>
              <div>
                <label className="field-label">Blood Group</label>
                <select
                  className="form-input"
                  value={medicalId.bloodGroup}
                  onChange={e => setMedicalId({...medicalId, bloodGroup: e.target.value})}
                >
                  <option value="A+ve">A+ve</option>
                  <option value="A-ve">A-ve</option>
                  <option value="B+ve">B+ve</option>
                  <option value="B-ve">B-ve</option>
                  <option value="O+ve">O+ve</option>
                  <option value="O-ve">O-ve (Universal Donor)</option>
                  <option value="AB+ve">AB+ve</option>
                  <option value="AB-ve">AB-ve</option>
                </select>
              </div>
              <div>
                <label className="field-label">Age</label>
                <input
                  type="number"
                  className="form-input"
                  value={medicalId.age}
                  onChange={e => setMedicalId({...medicalId, age: e.target.value})}
                />
              </div>
              <div>
                <label className="field-label">Organ Donor</label>
                <select
                  className="form-input"
                  value={medicalId.organDonor}
                  onChange={e => setMedicalId({...medicalId, organDonor: e.target.value})}
                >
                  <option value="Yes">Yes (Registered Donor)</option>
                  <option value="No">No</option>
                </select>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label className="field-label">Known Allergies</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Penicillin, Peanuts, Aspirin"
                  value={medicalId.allergies}
                  onChange={e => setMedicalId({...medicalId, allergies: e.target.value})}
                />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label className="field-label">Chronic Conditions & Implants</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Type 2 Diabetes, Pacemaker, Epilepsy"
                  value={medicalId.chronicConditions}
                  onChange={e => setMedicalId({...medicalId, chronicConditions: e.target.value})}
                />
              </div>
              <div>
                <label className="field-label">Emergency Contact Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={medicalId.emergencyContactName}
                  onChange={e => setMedicalId({...medicalId, emergencyContactName: e.target.value})}
                />
              </div>
              <div>
                <label className="field-label">Emergency Contact Phone</label>
                <input
                  type="tel"
                  className="form-input"
                  value={medicalId.emergencyContactPhone}
                  onChange={e => setMedicalId({...medicalId, emergencyContactPhone: e.target.value})}
                />
              </div>
              <div style={{ gridColumn: '1 / -1', marginTop: '10px' }}>
                <button type="submit" className="submit-predictor-btn">
                  Save Medical ID to Device Cache
                </button>
              </div>
            </form>
          ) : (
            <div style={{
              background: 'linear-gradient(135deg, #063940 0%, #0c4a6e 100%)',
              color: 'white',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 8px 24px rgba(6, 57, 64, 0.25)',
              position: 'relative'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.15)', paddingBottom: '14px', marginBottom: '16px' }}>
                <div>
                  <span style={{ background: '#ef4444', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 900, letterSpacing: '0.8px' }}>
                    EMERGENCY MEDICAL CARD
                  </span>
                  <h3 style={{ margin: '6px 0 0 0', fontSize: '1.4rem', fontWeight: 800 }}>{medicalId.fullName}</h3>
                  <span style={{ fontSize: '0.85rem', opacity: 0.85 }}>Age: {medicalId.age} yrs • Organ Donor: {medicalId.organDonor}</span>
                </div>
                <div style={{ textAlign: 'center', background: 'white', color: '#991b1b', padding: '8px 14px', borderRadius: '12px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 800, display: 'block' }}>BLOOD GROUP</span>
                  <strong style={{ fontSize: '1.4rem', fontWeight: 900 }}>{medicalId.bloodGroup}</strong>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', opacity: 0.75, textTransform: 'uppercase', fontWeight: 700 }}>Known Allergies</span>
                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fca5a5' }}>{medicalId.allergies || 'None Recorded'}</div>
                </div>
                <div>
                  <span style={{ fontSize: '0.75rem', opacity: 0.75, textTransform: 'uppercase', fontWeight: 700 }}>Chronic Conditions</span>
                  <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fed7aa' }}>{medicalId.chronicConditions || 'None Recorded'}</div>
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.1)', padding: '12px 16px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: '0.72rem', opacity: 0.8, display: 'block' }}>PRIMARY GUARDIAN CONTACT</span>
                  <strong style={{ fontSize: '0.95rem' }}>{medicalId.emergencyContactName}: {medicalId.emergencyContactPhone}</strong>
                </div>
                <a
                  href={`tel:${medicalId.emergencyContactPhone}`}
                  style={{ background: '#22c55e', color: 'white', textDecoration: 'none', padding: '6px 12px', borderRadius: '8px', fontWeight: 800, fontSize: '0.82rem' }}
                >
                  Direct Call
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: CACHED OFFLINE HOSPITAL DIRECTORY */}
      {activeOfflineTab === 'hospitals' && (
        <div style={{ background: 'white', borderRadius: '18px', border: '1px solid #e2e8f0', padding: '24px', boxShadow: '0 4px 14px rgba(0,0,0,0.05)' }}>
          <div style={{ marginBottom: '18px' }}>
            <h3 style={{ color: '#063940', fontSize: '1.25rem', fontWeight: 800, margin: '0 0 4px 0' }}>
              Offline Regional Emergency Hospital Directory
            </h3>
            <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0 }}>
              Pre-cached hospital contact numbers and addresses accessible with zero internet.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {offlineHospitals.map((hosp, idx) => (
              <div key={idx} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, color: '#063940', fontSize: '1.05rem', fontWeight: 800 }}>{hosp.name}</h4>
                  <span style={{ background: '#e0f2fe', color: '#0369a1', fontSize: '0.72rem', fontWeight: 800, padding: '2px 8px', borderRadius: '6px' }}>
                    {hosp.city}
                  </span>
                </div>
                <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '6px' }}>{hosp.addr}</div>
                <div style={{ fontSize: '0.8rem', color: '#07A3B2', fontWeight: 700, marginBottom: '12px' }}>{hosp.icu}</div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <a
                    href={`tel:${hosp.phone}`}
                    style={{
                      flex: 1,
                      textAlign: 'center',
                      background: '#dc2626',
                      color: 'white',
                      textDecoration: 'none',
                      padding: '8px',
                      borderRadius: '8px',
                      fontWeight: 800,
                      fontSize: '0.82rem'
                    }}
                  >
                    Emergency: {hosp.phone}
                  </a>
                  <a
                    href={`tel:${hosp.direct}`}
                    style={{
                      flex: 1,
                      textAlign: 'center',
                      background: '#063940',
                      color: 'white',
                      textDecoration: 'none',
                      padding: '8px',
                      borderRadius: '8px',
                      fontWeight: 800,
                      fontSize: '0.82rem'
                    }}
                  >
                    Direct Line
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

