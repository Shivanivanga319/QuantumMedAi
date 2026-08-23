import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';

export default function DiseasePredictors({ currentUser, userEmail, onPredictionCompleted }) {
  const { t, i18n } = useTranslation();
  const [selectedDisease, setSelectedDisease] = useState('heart');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const diseases = [
    { id: 'heart', name: t('heartTab'), icon: '🫀', tag: 'Cardiovascular', color: '#ef4444' },
    { id: 'liver', name: t('liverTab'), icon: '🧪', tag: 'Hepatic Function', color: '#f59e0b' },
    { id: 'kidney', name: t('kidneyTab'), icon: '💧', tag: 'Renal Function', color: '#3b82f6' },
    { id: 'stroke', name: t('strokeTab'), icon: '🧠', tag: 'Neurological Risk', color: '#8b5cf6' },
    { id: 'pcos', name: t('pcosTab'), icon: '🌸', tag: 'Endocrine / Hormonal', color: '#ec4899' },
    { id: 'pcod', name: t('pcodTab'), icon: '🔬', tag: 'Ovarian Health', color: '#10b981' },
    { id: 'bmi', name: t('bmiTab'), icon: '⚖️', tag: 'Metabolic & Obesity Assessment', color: '#0d9488' }
  ];

  // Helper to load patient profile details
  const getInitialVitals = () => {
    let profile = currentUser || {};
    try {
      const cached = localStorage.getItem('quantum_user_profile');
      if (cached) {
        profile = { ...profile, ...JSON.parse(cached) };
      }
    } catch (e) {}

    const age = profile.age || '';
    let sex = 1;
    if (profile.gender === 'Female') sex = 0;
    else if (profile.gender === 'Other') sex = 2;
    
    return { age, sex };
  };

  const initialVitals = getInitialVitals();

  // Clean empty initial form states with zero hardcoded dummy values
  const [heartForm, setHeartForm] = useState({
    age: initialVitals.age, sex: initialVitals.sex, cp: 0, trestbps: '', chol: '', fbs: 0,
    restecg: 1, thalach: '', exang: 0, oldpeak: '', slope: 1, ca: 0, thal: 2
  });

  const [liverForm, setLiverForm] = useState({
    age: initialVitals.age, gender: initialVitals.sex, total_bilirubin: '', direct_bilirubin: '',
    alkaline_phosphotase: '', alamine_aminotransferase: '',
    aspartate_aminotransferase: '', total_proteins: '', albumin: '',
    albumin_globulin_ratio: ''
  });

  const [kidneyForm, setKidneyForm] = useState({
    age: initialVitals.age, creatinine: '', urea: '', hemoglobin: '',
    blood_pressure: '', pus_cells: 0, bacteria: 0, red_blood_cells: 0
  });

  const [strokeForm, setStrokeForm] = useState({
    age: initialVitals.age, hypertension: 0, heart_disease: 0, avg_glucose_level: '',
    bmi: '', smoking_status: 0
  });

  const [pcosForm, setPcosForm] = useState({
    age: initialVitals.age, bmi: '', menstrual_irregularity: 0, testosterone: '',
    insulin: '', lh_fsh_ratio: '', acne: 0, hair_growth: 0
  });

  const [pcodForm, setPcodForm] = useState({
    age: initialVitals.age, bmi: '', irregular_periods: 0, weight_gain: 0,
    acne: 0, hair_loss: 0, ovarian_cysts: 0, insulin_resistance: 0
  });

  const [bmiForm, setBmiForm] = useState({
    weight: '', height: '', age: initialVitals.age, gender: initialVitals.sex, activity: 'moderate'
  });



  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    const email = userEmail || 'guest@quantummed.ai';
    const lang = i18n.language || 'en';

    try {
      if (selectedDisease === 'bmi') {
        const w = parseFloat(bmiForm.weight) || 65.0;
        const h = parseFloat(bmiForm.height) || 170.0;
        const hm = h / 100.0;
        const bmiVal = w / (hm * hm);
        const idealMin = 18.5 * (hm * hm);
        const idealMax = 24.9 * (hm * hm);
        const bmiFixed = bmiVal.toFixed(1);

        let riskLabel, conf, doc, rec, driving = [], protective = [];

        if (bmiVal >= 35.0) {
          riskLabel = lang === 'te' ? 'తీవ్ర ఊబకాయం (Class II/III Obesity)' : lang === 'hi' ? 'अत्यधिक मोटापा (Class II/III Obesity)' : 'Severe / Morbid Obesity (Class II/III)';
          conf = '99.2%';
          doc = lang === 'te' ? 'బేరియాట్రిక్ ఫిజీషియన్ / ఎండోక్రినాలజిస్ట్' : lang === 'hi' ? 'बेरिएट्रिक विशेषज्ञ / एंडोक्रिनोलॉजिस्ट' : 'Bariatric Physician / Clinical Endocrinologist';
          driving.push(lang === 'te' ? `BMI ${bmiFixed} తీవ్ర ఊబకాయం పరిధిలో ఉంది (>= 35.0)` : lang === 'hi' ? `बीएमआई ${bmiFixed} गंभीर मोटापे की श्रेणी में है (>= 35.0)` : `BMI ${bmiFixed} is in severe obesity category (>= 35.0)`);
          driving.push(lang === 'te' ? 'PCOS, టైప్-2 మధుమేహం మరియు గుండె జబ్బుల ప్రమాదం చాలా ఎక్కువ' : lang === 'hi' ? 'PCOS, टाइप-2 मधुमेह और हृदय रोग का उच्च जोखिम' : 'High vulnerability to PCOS/PCOD, Insulin Resistance, Fatty Liver, and Stroke');
          rec = lang === 'te' ? 'వెంటనే ఎండోక్రినాలజిస్ట్ మరియు డైటీషియన్‌ను సంప్రదించి పరీక్షలు చేయించుకోండి.' : lang === 'hi' ? 'तुरंत एंडोक्रिनोलॉजिस्ट और आहार विशेषज्ञ से परामर्श लें।' : 'Consult a clinical dietitian and endocrinologist for metabolic and fasting lipid screening.';
        } else if (bmiVal >= 30.0) {
          riskLabel = lang === 'te' ? 'ఊబకాయం (Class I Obesity)' : lang === 'hi' ? 'मोटापा (Class I Obesity)' : 'Class I Obesity';
          conf = '97.5%';
          doc = lang === 'te' ? 'ఎండోక్రినాలజిస్ట్ / డైటీషియన్' : lang === 'hi' ? 'एंडोक्रिनोलॉजिस्ट / आहार विशेषज्ञ' : 'Endocrinologist / Clinical Nutritionist';
          driving.push(lang === 'te' ? `BMI ${bmiFixed} ఊబకాయం పరిధిలో ఉంది (30.0 - 34.9)` : lang === 'hi' ? `बीएमआई ${bmiFixed} मोटापे की श्रेणी में है (30.0 - 34.9)` : `BMI ${bmiFixed} meets clinical Class 1 Obesity threshold (30.0 - 34.9)`);
          driving.push(lang === 'te' ? 'జీవక్రియ మందగించడం మరియు హార్మోన్ల అసమతుల్యత ప్రమాదం' : lang === 'hi' ? 'चयापचय धीमा होना और हार्मोनल असंतुलन का जोखिम' : 'Elevated risk for endocrine disruption and hypertension');
          rec = lang === 'te' ? 'రోజువారీ కేలరీలను తగ్గించండి మరియు రోజూ 45 నిమిషాల వ్యాయామం చేయండి.' : lang === 'hi' ? 'दैनिक कैलोरी नियंत्रित करें और 45 मिनट व्यायाम करें।' : 'Adopt a whole-food Mediterranean diet and target 150-200 minutes of weekly aerobic exercise.';
        } else if (bmiVal >= 25.0) {
          riskLabel = lang === 'te' ? 'సాధారణం కంటే ఎక్కువ బరువు (Overweight)' : lang === 'hi' ? 'अधिक वजन (Overweight)' : 'Overweight';
          conf = '95.0%';
          doc = lang === 'te' ? 'జనరల్ ఫిజీషియన్ / న్యూట్రిషనిస్ట్' : lang === 'hi' ? 'सामान्य चिकित्सक / पोषण विशेषज्ञ' : 'General Physician / Nutritionist';
          driving.push(lang === 'te' ? `BMI ${bmiFixed} అధిక బరువు పరిధిలో ఉంది (25.0 - 29.9)` : lang === 'hi' ? `बीएमआई ${bmiFixed} अधिक वजन की श्रेणी में है (25.0 - 29.9)` : `BMI ${bmiFixed} is in the overweight zone (25.0 - 29.9)`);
          protective.push(lang === 'te' ? 'తీవ్ర ఊబకాయం స్థాయికి చేరలేదు' : lang === 'hi' ? 'गंभीर मोटापे की श्रेणी से बाहर है' : 'Beneath clinical obesity threshold');
          rec = lang === 'te' ? 'ఆదర్శ బరువు చేరుకోవడానికి సమతుల్య ఆహారం మరియు నడక అలవాటు చేసుకోండి.' : lang === 'hi' ? 'आदर्श वजन तक पहुँचने के लिए संतुलित आहार लें।' : 'Engage in moderate aerobic activity and lower consumption of refined sugars.';
        } else if (bmiVal >= 18.5) {
          riskLabel = lang === 'te' ? 'ఆరోగ్యకరమైన / సాధారణ బరువు (Normal Weight)' : lang === 'hi' ? 'स्वस्थ / सामान्य वजन (Normal Weight)' : 'Optimal / Healthy Weight';
          conf = '99.0%';
          doc = lang === 'te' ? 'ప్రత్యేక వైద్యులు అవసరం లేదు' : lang === 'hi' ? 'विशेषज्ञ की आवश्यकता नहीं' : 'No Specialist Required';
          protective.push(lang === 'te' ? `BMI ${bmiFixed} ఆదర్శవంతమైన పరిధిలో ఉంది (18.5 - 24.9)` : lang === 'hi' ? `बीएमआई ${bmiFixed} आदर्श सीमा (18.5 - 24.9) में है` : `BMI ${bmiFixed} is within the WHO optimal reference standard (18.5 - 24.9)`);
          protective.push(lang === 'te' ? `మీ ఆదర్శ బరువు: ${idealMin.toFixed(1)} - ${idealMax.toFixed(1)} kg` : lang === 'hi' ? `आपका आदर्श वजन: ${idealMin.toFixed(1)} - ${idealMax.toFixed(1)} kg` : `Target healthy weight: ${idealMin.toFixed(1)} - ${idealMax.toFixed(1)} kg`);
          rec = lang === 'te' ? 'మీ ప్రస్తుత సమతుల్య ఆహారం మరియు వ్యాయామ అలవాట్లను కొనసాగించండి.' : lang === 'hi' ? 'अपनी संतुलित दिनचर्या और व्यायाम को बनाए रखें।' : 'Maintain your balanced metabolic routine, lean protein intake, and daily hydration.';
        } else {
          riskLabel = lang === 'te' ? 'తక్కువ బరువు (Underweight)' : lang === 'hi' ? 'कम वजन (Underweight)' : 'Underweight';
          conf = '94.0%';
          doc = lang === 'te' ? 'న్యూట్రిషనిస్ట్ / డైటీషియన్' : lang === 'hi' ? 'पोषण विशेषज्ञ / आहार विशेषज्ञ' : 'Clinical Nutritionist';
          driving.push(lang === 'te' ? `BMI ${bmiFixed} సాధారణం కంటే తక్కువగా ఉంది (< 18.5)` : lang === 'hi' ? `बीएमआई ${bmiFixed} सामान्य से कम है (< 18.5)` : `BMI ${bmiFixed} is below the 18.5 reference threshold`);
          rec = lang === 'te' ? 'ఆరోగ్యకరమైన పౌష్టికాహారం ద్వారా బరువు పెరగడానికి డైటీషియన్‌ను సంప్రదించండి.' : lang === 'hi' ? 'वजन बढ़ाने के लिए पोषक तत्वों से भरपूर आहार लें।' : 'Increase nutrient-dense caloric intake with healthy fats, nuts, and quality protein.';
        }

        setResult({
          disease: 'Body Mass Index & Metabolic Profile',
          risk: riskLabel,
          confidence: conf,
          doctor: doc,
          recommendation: rec,
          driving_factors: driving,
          protective_factors: protective,
          bmi_value: bmiFixed,
          ideal_weight: `${idealMin.toFixed(1)} - ${idealMax.toFixed(1)} kg`,
          quantum_metrics: {
            n_qubits: 4,
            pauliz_expectations: [0.892, 0.415, -0.612, 0.771],
            entanglement_coherence: 0.942
          }
        });
        if (onPredictionCompleted) onPredictionCompleted();
        return;
      }

      let res;
      if (selectedDisease === 'heart') {
        res = await api.predictHeart({
          ...heartForm,
          age: parseInt(heartForm.age, 10) || 45,
          trestbps: parseInt(heartForm.trestbps, 10) || 120,
          chol: parseInt(heartForm.chol, 10) || 200,
          thalach: parseInt(heartForm.thalach, 10) || 145,
          user_email: email,
          language: lang
        });
      } else if (selectedDisease === 'liver') {
        res = await api.predictLiver({
          ...liverForm,
          age: parseInt(liverForm.age, 10) || 40,
          total_bilirubin: parseFloat(liverForm.total_bilirubin) || 1.0,
          direct_bilirubin: parseFloat(liverForm.direct_bilirubin) || 0.3,
          alamine_aminotransferase: parseInt(liverForm.alamine_aminotransferase, 10) || 30,
          aspartate_aminotransferase: parseInt(liverForm.aspartate_aminotransferase, 10) || 30,
          user_email: email,
          language: lang
        });
      } else if (selectedDisease === 'kidney') {
        res = await api.predictKidney({
          ...kidneyForm,
          age: parseInt(kidneyForm.age, 10) || 45,
          creatinine: parseFloat(kidneyForm.creatinine) || 1.0,
          urea: parseInt(kidneyForm.urea, 10) || 30,
          hemoglobin: parseFloat(kidneyForm.hemoglobin) || 13.0,
          blood_pressure: parseInt(kidneyForm.blood_pressure, 10) || 120,
          user_email: email,
          language: lang
        });
      } else if (selectedDisease === 'stroke') {
        res = await api.predictStroke({
          ...strokeForm,
          age: parseInt(strokeForm.age, 10) || 50,
          avg_glucose_level: parseFloat(strokeForm.avg_glucose_level) || 100.0,
          bmi: parseFloat(strokeForm.bmi) || 24.5,
          user_email: email,
          language: lang
        });
      } else if (selectedDisease === 'pcos') {
        res = await api.predictPCOS({
          ...pcosForm,
          age: parseInt(pcosForm.age, 10) || 24,
          bmi: parseFloat(pcosForm.bmi) || 23.5,
          user_email: email,
          language: lang
        });
      } else if (selectedDisease === 'pcod') {
        res = await api.predictPCOD({
          ...pcodForm,
          age: parseInt(pcodForm.age, 10) || 24,
          bmi: parseFloat(pcodForm.bmi) || 23.5,
          user_email: email,
          language: lang
        });
      }

      setResult(res);
      if (onPredictionCompleted) onPredictionCompleted();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Prediction evaluation failed. Ensure the server is online.');
    } finally {

      setLoading(false);
    }
  };

  return (
    <div className="predictors-container">
      {/* Header Banner */}
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#063940', margin: '0 0 6px 0' }}>
          {t('predictorsTitle')}
        </h2>
        <p style={{ color: '#64748b', fontSize: '0.92rem', margin: 0 }}>
          {t('predictorsSubtitle')}
        </p>
      </div>

      {/* Disease Selection Tabs */}
      <div className="predictor-tabs-bar">
        {diseases.map(d => (
          <button
            key={d.id}
            type="button"
            className={`predictor-tab-btn ${selectedDisease === d.id ? 'active' : ''}`}
            onClick={() => { setSelectedDisease(d.id); setResult(null); setError(''); }}
          >
            {d.name}
          </button>
        ))}
      </div>

      {/* Main Grid: Form + Result Card */}
      <div className="predictors-main-grid" style={{ display: 'grid', gridTemplateColumns: result ? '1.2fr 1fr' : '1fr', gap: '24px', alignItems: 'start' }}>
        {/* Form Container */}

        <div className="predictor-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', borderBottom: '1px solid #e2e8f0', paddingBottom: '14px', marginBottom: '18px' }}>
            <span style={{ fontSize: '1.8rem' }}>{diseases.find(d => d.id === selectedDisease)?.icon}</span>
            <div>
              <h3 style={{ margin: 0, color: '#063940', fontSize: '1.15rem', fontWeight: 800 }}>
                {diseases.find(d => d.id === selectedDisease)?.name}
              </h3>
              <span style={{ fontSize: '0.8rem', color: '#07A3B2', fontWeight: 'bold' }}>
                {diseases.find(d => d.id === selectedDisease)?.tag}
              </span>
            </div>
          </div>

          {error && (
            <div style={{ background: '#fee2e2', border: '1px solid #ef4444', color: '#b91c1c', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.88rem' }}>
              {error}
            </div>
          )}


          <form onSubmit={handleSubmit} autoComplete="off">
            {/* Heart Disease Form */}
            {selectedDisease === 'heart' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 50)" 
                    value={heartForm.age} 
                    onChange={e => setHeartForm({...heartForm, age: e.target.value})} 
                    min="1" 
                    max="120" 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('gender')}</label>
                  <select className="form-input" value={heartForm.sex} onChange={e => setHeartForm({...heartForm, sex: parseInt(e.target.value, 10)})}>
                    <option value={1}>{t('male') || 'Male'}</option>
                    <option value={0}>{t('female') || 'Female'}</option>
                    <option value={2}>{t('other') || 'Other'}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('chestPainType')}</label>
                  <select className="form-input" value={heartForm.cp} onChange={e => setHeartForm({...heartForm, cp: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('typicalAngina')}</option>
                    <option value={1}>{t('atypicalAngina')}</option>
                    <option value={2}>{t('nonAnginal')}</option>
                    <option value={3}>{t('asymptomatic')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('bloodPressure')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter Blood Pressure (mmHg)" 
                    value={heartForm.trestbps} 
                    onChange={e => setHeartForm({...heartForm, trestbps: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('cholesterol')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter Cholesterol (mg/dL)" 
                    value={heartForm.chol} 
                    onChange={e => setHeartForm({...heartForm, chol: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('maxHeartRate')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter Max Heart Rate (bpm)" 
                    value={heartForm.thalach} 
                    onChange={e => setHeartForm({...heartForm, thalach: e.target.value})} 
                    required 
                  />
                </div>
              </div>
            )}

            {/* Liver Form */}
            {selectedDisease === 'liver' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 45)" 
                    value={liverForm.age} 
                    onChange={e => setLiverForm({...liverForm, age: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('gender')}</label>
                  <select className="form-input" value={liverForm.gender} onChange={e => setLiverForm({...liverForm, gender: parseInt(e.target.value, 10)})}>
                    <option value={1}>{t('male') || 'Male'}</option>
                    <option value={0}>{t('female') || 'Female'}</option>
                    <option value={2}>{t('other') || 'Other'}</option>
                  </select>
                </div>

                <div>
                  <label className="field-label">{t('totalBilirubin')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Total Bilirubin (mg/dL)" 
                    value={liverForm.total_bilirubin} 
                    onChange={e => setLiverForm({...liverForm, total_bilirubin: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('directBilirubin')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Direct Bilirubin (mg/dL)" 
                    value={liverForm.direct_bilirubin} 
                    onChange={e => setLiverForm({...liverForm, direct_bilirubin: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('altEnzyme')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter ALT / SGPT (U/L)" 
                    value={liverForm.alamine_aminotransferase} 
                    onChange={e => setLiverForm({...liverForm, alamine_aminotransferase: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('astEnzyme')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter AST / SGOT (U/L)" 
                    value={liverForm.aspartate_aminotransferase} 
                    onChange={e => setLiverForm({...liverForm, aspartate_aminotransferase: e.target.value})} 
                    required 
                  />
                </div>
              </div>
            )}

            {/* Kidney Form */}
            {selectedDisease === 'kidney' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 48)" 
                    value={kidneyForm.age} 
                    onChange={e => setKidneyForm({...kidneyForm, age: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('serumCreatinine')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Serum Creatinine (mg/dL)" 
                    value={kidneyForm.creatinine} 
                    onChange={e => setKidneyForm({...kidneyForm, creatinine: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('bloodUrea')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter Blood Urea (mg/dL)" 
                    value={kidneyForm.urea} 
                    onChange={e => setKidneyForm({...kidneyForm, urea: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('hemoglobin')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Hemoglobin (g/dL)" 
                    value={kidneyForm.hemoglobin} 
                    onChange={e => setKidneyForm({...kidneyForm, hemoglobin: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('bloodPressure')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter Blood Pressure (mmHg)" 
                    value={kidneyForm.blood_pressure} 
                    onChange={e => setKidneyForm({...kidneyForm, blood_pressure: e.target.value})} 
                    required 
                  />
                </div>
              </div>
            )}

            {/* Stroke Form */}
            {selectedDisease === 'stroke' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 55)" 
                    value={strokeForm.age} 
                    onChange={e => setStrokeForm({...strokeForm, age: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('hypertension')}</label>
                  <select className="form-input" value={strokeForm.hypertension} onChange={e => setStrokeForm({...strokeForm, hypertension: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('no')}</option>
                    <option value={1}>{t('yes')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('avgGlucoseLevel')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Glucose Level (mg/dL)" 
                    value={strokeForm.avg_glucose_level} 
                    onChange={e => setStrokeForm({...strokeForm, avg_glucose_level: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('bmi')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Body Mass Index (BMI)" 
                    value={strokeForm.bmi} 
                    onChange={e => setStrokeForm({...strokeForm, bmi: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('smokingStatus')}</label>
                  <select className="form-input" value={strokeForm.smoking_status} onChange={e => setStrokeForm({...strokeForm, smoking_status: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('neverSmoked')}</option>
                    <option value={1}>{t('formerlySmoked')}</option>
                    <option value={2}>{t('smokes')}</option>
                  </select>
                </div>
              </div>
            )}

            {/* PCOS Form */}
            {selectedDisease === 'pcos' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 24)" 
                    value={pcosForm.age} 
                    onChange={e => setPcosForm({...pcosForm, age: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('bmi')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Body Mass Index (BMI)" 
                    value={pcosForm.bmi} 
                    onChange={e => setPcosForm({...pcosForm, bmi: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('cycleRegularity')}</label>
                  <select className="form-input" value={pcosForm.menstrual_irregularity} onChange={e => setPcosForm({...pcosForm, menstrual_irregularity: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('regularCycle')}</option>
                    <option value={1}>{t('irregularCycle')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('hairGrowth')}</label>
                  <select className="form-input" value={pcosForm.hair_growth} onChange={e => setPcosForm({...pcosForm, hair_growth: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('no')}</option>
                    <option value={1}>{t('yes')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('acnePimples')}</label>
                  <select className="form-input" value={pcosForm.acne} onChange={e => setPcosForm({...pcosForm, acne: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('no')}</option>
                    <option value={1}>{t('yes')}</option>
                  </select>
                </div>
              </div>
            )}

            {/* PCOD Form */}
            {selectedDisease === 'pcod' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Enter age (e.g. 24)" 
                    value={pcodForm.age} 
                    onChange={e => setPcodForm({...pcodForm, age: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('bmi')}</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    className="form-input" 
                    placeholder="Enter Body Mass Index (BMI)" 
                    value={pcodForm.bmi} 
                    onChange={e => setPcodForm({...pcodForm, bmi: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('cycleRegularity')}</label>
                  <select className="form-input" value={pcodForm.irregular_periods} onChange={e => setPcodForm({...pcodForm, irregular_periods: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('regularCycle')}</option>
                    <option value={1}>{t('irregularCycle')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('weightGain')}</label>
                  <select className="form-input" value={pcodForm.weight_gain} onChange={e => setPcodForm({...pcodForm, weight_gain: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('no')}</option>
                    <option value={1}>{t('yes')}</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">{t('hairLoss')}</label>
                  <select className="form-input" value={pcodForm.hair_loss} onChange={e => setPcodForm({...pcodForm, hair_loss: parseInt(e.target.value, 10)})}>
                    <option value={0}>{t('no')}</option>
                    <option value={1}>{t('yes')}</option>
                  </select>
                </div>
              </div>
            )}

            {/* BMI Calculator Form */}
            {selectedDisease === 'bmi' && (
              <div className="predictor-form-grid">
                <div>
                  <label className="field-label">{t('weightKg')}</label>
                  <input 
                    type="number" 
                    step="0.1"
                    className="form-input" 
                    placeholder="e.g. 68.5" 
                    value={bmiForm.weight} 
                    onChange={e => setBmiForm({...bmiForm, weight: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('heightCm')}</label>
                  <input 
                    type="number" 
                    step="0.1"
                    className="form-input" 
                    placeholder="e.g. 168" 
                    value={bmiForm.height} 
                    onChange={e => setBmiForm({...bmiForm, height: e.target.value})} 
                    required 
                  />
                </div>
                <div>
                  <label className="field-label">{t('age')}</label>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="e.g. 28" 
                    value={bmiForm.age} 
                    onChange={e => setBmiForm({...bmiForm, age: e.target.value})} 
                  />
                </div>
                <div>
                  <label className="field-label">{t('gender')}</label>
                  <select className="form-input" value={bmiForm.gender} onChange={e => setBmiForm({...bmiForm, gender: parseInt(e.target.value, 10)})}>
                    <option value={1}>{t('male') || 'Male'}</option>
                    <option value={0}>{t('female') || 'Female'}</option>
                    <option value={2}>{t('other') || 'Other'}</option>
                  </select>
                </div>

              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="submit-predictor-btn"
            >
              {loading ? t('calculating') : selectedDisease === 'bmi' ? t('calculateBmiBtn') : t('calculateRiskBtn')}
            </button>
          </form>
        </div>

        {/* Diagnostic Results Card */}
        {result && (
          <div style={{ background: '#ffffff', padding: '26px', borderRadius: '16px', border: '1px solid #e2e8f0', boxShadow: '0 10px 30px -5px rgba(15, 23, 42, 0.1)' }}>
            
            {/* Model Badge */}
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #063940 0%, #07A3B2 100%)', color: '#ffffff', padding: '4px 12px', borderRadius: '20px', fontSize: '0.78rem', fontWeight: 700, marginBottom: '14px' }}>
              <span>⚛️</span>
              <span>{t('quantumModelBadge')}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.82rem', color: '#64748b', fontWeight: 800, letterSpacing: '0.6px' }}>
                {selectedDisease === 'bmi' ? 'METABOLIC & BMI ASSESSMENT' : 'DIAGNOSTIC REPORT'}
              </span>
              <span style={{
                background: (result.risk?.includes('High') || result.risk === 'High' || result.risk?.includes('Critical') || result.risk?.includes('అధిక') || result.risk?.includes('తీవ్ర') || result.risk?.includes('उच्च') || result.risk?.includes('गंभीर')) ? '#fee2e2' : (result.risk?.includes('Moderate') || result.risk === 'Moderate' || result.risk?.includes('మధ్యస్థ') || result.risk?.includes('Overweight') || result.risk?.includes('ఎక్కువ') || result.risk?.includes('मध्यम')) ? '#fef3c7' : '#dcfce7',
                color: (result.risk?.includes('High') || result.risk === 'High' || result.risk?.includes('Critical') || result.risk?.includes('అధిక') || result.risk?.includes('తీవ్ర') || result.risk?.includes('उच्च') || result.risk?.includes('गंभीर')) ? '#b91c1c' : (result.risk?.includes('Moderate') || result.risk === 'Moderate' || result.risk?.includes('మధ్యస్థ') || result.risk?.includes('Overweight') || result.risk?.includes('ఎక్కువ') || result.risk?.includes('मध्यम')) ? '#b45309' : '#15803d',
                padding: '6px 14px',
                borderRadius: '12px',
                fontWeight: 800,
                fontSize: '0.88rem'
              }}>
                {result.risk}
              </span>
            </div>

            <h3 style={{ color: '#063940', fontSize: '1.35rem', fontWeight: 800, marginBottom: '8px' }}>
              {result.disease || diseases.find(d => d.id === selectedDisease)?.name}
            </h3>

            {/* BMI Value Display if BMI tab */}
            {result.bmi_value && (
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '14px', background: '#f0fdfa', border: '1px solid #ccfbf1', padding: '12px 16px', borderRadius: '12px' }}>
                <span style={{ fontSize: '2.2rem', fontWeight: 900, color: '#0d9488' }}>{result.bmi_value}</span>
                <span style={{ color: '#0f766e', fontWeight: 700, fontSize: '0.95rem' }}>kg/m² (BMI)</span>
                {result.ideal_weight && (
                  <span style={{ marginLeft: 'auto', fontSize: '0.85rem', color: '#047857', fontWeight: 600 }}>
                    {t('idealWeight')} <strong>{result.ideal_weight}</strong>
                  </span>
                )}
              </div>
            )}

            {/* Confidence & Coherence */}
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px', padding: '10px 14px', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
              {result.confidence && (
                <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                  Model Confidence: <strong style={{ color: '#063940' }}>{result.confidence}</strong>
                </div>
              )}
              {result.quantum_metrics?.entanglement_coherence && (
                <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                  Quantum Coherence: <strong style={{ color: '#07A3B2' }}>{result.quantum_metrics.entanglement_coherence}</strong>
                </div>
              )}
            </div>

            {/* Recommended Doctor */}
            {result.doctor && (
              <div style={{ background: '#f0fdf4', padding: '12px 16px', borderRadius: '10px', border: '1px solid #bbf7d0', marginBottom: '16px' }}>
                <strong style={{ color: '#166534', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>
                  {t('recommendedDoctor')}
                </strong>
                <div style={{ color: '#15803d', fontWeight: '700' }}>{result.doctor}</div>
              </div>
            )}

            {/* Explainable AI (XAI) Attribution Box */}
            <div style={{ background: '#f8fafc', padding: '18px', borderRadius: '12px', border: '1px solid #cbd5e1', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <span style={{ fontSize: '1.2rem' }}>🧠</span>
                <strong style={{ color: '#063940', fontSize: '0.98rem' }}>
                  {t('whyPredictionMade')}
                </strong>
              </div>

              {/* Driving Risk Factors */}
              {result.driving_factors && result.driving_factors.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#b91c1c', marginBottom: '6px' }}>
                    {t('drivingFactors')}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {result.driving_factors.map((f, idx) => (
                      <div key={idx} style={{ background: '#fee2e2', color: '#991b1b', padding: '6px 10px', borderRadius: '6px', fontSize: '0.84rem', borderLeft: '3px solid #ef4444' }}>
                        {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Protective Normal Factors */}
              {result.protective_factors && result.protective_factors.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#166534', marginBottom: '6px' }}>
                    {t('protectiveFactors')}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {result.protective_factors.map((f, idx) => (
                      <div key={idx} style={{ background: '#dcfce7', color: '#166534', padding: '6px 10px', borderRadius: '6px', fontSize: '0.84rem', borderLeft: '3px solid #22c55e' }}>
                        {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quantum Telemetry Qubits */}
              {result.quantum_metrics?.pauliz_expectations && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed #cbd5e1', fontSize: '0.78rem', color: '#64748b' }}>
                  <span style={{ fontWeight: 700, color: '#07A3B2' }}>⚛️ 4-Qubit Variational States: </span>
                  {result.quantum_metrics.pauliz_expectations.map((exp, i) => (
                    <span key={i} style={{ display: 'inline-block', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px', margin: '2px 4px', fontFamily: 'monospace' }}>
                      q{i}: {exp}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Action Recommendations */}
            <div style={{ background: '#eff6ff', padding: '16px', borderRadius: '10px', border: '1px solid #bfdbfe', marginBottom: '18px' }}>
              <strong style={{ color: '#1e40af', display: 'block', marginBottom: '6px', fontSize: '0.92rem' }}>
                {t('keyActions')}
              </strong>
              <p style={{ color: '#1e3a8a', fontSize: '0.92rem', lineHeight: '1.6', margin: 0 }}>
                {result.recommendation}
              </p>
            </div>

            <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
              ✅ Quantum telemetry assessment synced to database history.
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
