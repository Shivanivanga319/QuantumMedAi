const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
  }
  return 'https://quantummedai.onrender.com';
};

const API_BASE_URL = getApiBaseUrl();


const getAuthHeaders = () => {
  const sessionString = localStorage.getItem('quantum_session');
  if (sessionString) {
    try {
      const session = JSON.parse(sessionString);
      if (session.token) {
        return {
          'Authorization': `Bearer ${session.token}`,
          'Content-Type': 'application/json'
        };
      }
    } catch (e) {
      console.error("Error parsing session:", e);
    }
  }
  return {
    'Content-Type': 'application/json'
  };
};

const handleResponse = async (response) => {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
    throw new Error(errorMsg);
  }
  return data;
};

export const api = {
  // Authentication
  login: async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: (email || '').trim().toLowerCase(), password })
    });
    return handleResponse(response);
  },

  register: async (userData) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: (userData.fullName || userData.full_name || '').trim(),
        email: (userData.email || '').trim().toLowerCase(),
        password: userData.password,
        gender: userData.gender || null,
        age: userData.age ? parseInt(userData.age, 10) : null,
        phone: userData.phone || null
      })
    });
    return handleResponse(response);
  },

  getCurrentUser: async () => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    return handleResponse(response);
  },

  // Disease Predictions
  predictHeart: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/heart/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictLiver: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/liver/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictKidney: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/kidney/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictStroke: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/stroke/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictPcos: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/pcos/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictPCOS: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/pcos/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictPcod: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/pcod/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  predictPCOD: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/pcod/predict`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },


  // Emergency Triage, Geo-Hospitals & SMS Dispatch
  checkEmergency: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/emergency/check`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  getNearbyHospitals: async (lat, lng, radius_km = 35.0, specialty = null, city = null, scheme = null) => {
    let url = `${API_BASE_URL}/emergency/nearby-hospitals?lat=${lat}&lng=${lng}&radius_km=${radius_km}`;
    if (specialty && specialty !== 'All') {
      url += `&specialty=${encodeURIComponent(specialty)}`;
    }
    if (city && city !== 'All') {
      url += `&city=${encodeURIComponent(city)}`;
    }
    if (scheme && scheme !== 'All') {
      url += `&scheme=${encodeURIComponent(scheme)}`;
    }
    const response = await fetch(url, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    return handleResponse(response);
  },

  sendHospitalPreAlert: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/emergency/pre-alert`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },

  dispatchSmsAlert: async (payload) => {
    const response = await fetch(`${API_BASE_URL}/emergency/sms-dispatch`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    return handleResponse(response);
  },



  // AI NLP Symptom Consultation & Report Analysis
  analyzeSymptoms: async ({ text, user_email, document_name, image_base64, mime_type, language, history }) => {
    const response = await fetch(`${API_BASE_URL}/predictions/symptoms`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        text,
        user_email: user_email || 'guest@quantummed.ai',
        document_name: document_name || null,
        image_base64: image_base64 || null,
        mime_type: mime_type || 'image/jpeg',
        language: language || 'en',
        history: history || []
      })
    });
    return handleResponse(response);
  },

  // Direct Medical Image / Document Upload
  uploadDocument: async ({ file, query, user_email, language }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('query', query || '');
    formData.append('user_email', user_email || 'guest@quantummed.ai');
    formData.append('language', language || 'en');

    const token = localStorage.getItem('token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    const response = await fetch(`${API_BASE_URL}/predictions/upload-document`, {
      method: 'POST',
      headers,
      body: formData
    });
    return handleResponse(response);
  },


  // AI Engine Status
  getAiStatus: async () => {
    const response = await fetch(`${API_BASE_URL}/predictions/status`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    return handleResponse(response);
  },

  // Medical Prediction History
  getHistory: async (email) => {

    const query = email ? `?email=${encodeURIComponent(email.trim())}` : '';
    const response = await fetch(`${API_BASE_URL}/predictions/history${query}`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    return handleResponse(response);
  }
};

export default api;
