const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

let customTokenGetter = null;

export const setAuthTokenGetter = (getterFn) => {
  customTokenGetter = getterFn;
};

const getAuthToken = () => {
  if (customTokenGetter) {
    const t = customTokenGetter();
    if (t) return t;
  }
  if (typeof window !== 'undefined' && window.localStorage) {
    return localStorage.getItem('lb_auth_token') || null;
  }
  return null;
};

async function request(path, options = {}) {
  const token = getAuthToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const url = `${API_BASE}${path}`;
  
  // Timeout protection
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || 20000);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: options.signal || controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.message || errorDetail;
      } catch {
        const text = await response.text();
        if (text) errorDetail = text;
      }
      const error = new Error(errorDetail);
      error.status = response.status;
      throw error;
    }

    // If response is PDF blob
    if (response.headers.get('content-type')?.includes('application/pdf')) {
      return response.blob();
    }

    // If 204 No Content
    if (response.status === 204) {
      return null;
    }

    return response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. Please check your network connection.');
    }
    throw err;
  }
}

export const api = {
  // Auth & Profile
  register: (email, password, fullName) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, full_name: fullName }),
  }),
  login: (email, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  checkHealth: () => request('/health'),
  getMe: () => request('/me'),
  updateProfile: (fullName) => request('/me/profile', {
    method: 'PATCH',
    body: JSON.stringify({ full_name: fullName }),
  }),

  // Deals

  getDashboardStats: () => request('/deals/stats'),
  getDeals: (params = {}) => {
    const searchParams = new URLSearchParams();
    if (params.q) searchParams.append('q', params.q);
    if (params.category && params.category !== 'all') searchParams.append('category', params.category);
    if (params.status && params.status !== 'all') searchParams.append('status', params.status);
    const queryString = searchParams.toString();
    return request(`/deals${queryString ? `?${queryString}` : ''}`);
  },
  getDeal: (dealId) => request(`/deals/${dealId}`),
  createDeal: (payload) => request('/deals', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateDeal: (dealId, payload) => request(`/deals/${dealId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
  deleteDeal: (dealId) => request(`/deals/${dealId}`, {
    method: 'DELETE',
  }),


  // Invitations
  createInvitation: (dealId, payload) => request(`/deals/${dealId}/invitations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getInvitationInfo: (token) => request(`/invitations/${token}/info`),
  acceptInvitation: (token) => request(`/invitations/${token}/accept`, {
    method: 'POST',
  }),

  // Conversations & AI Analysis
  getConversations: (dealId) => request(`/deals/${dealId}/conversations`),
  importConversation: (dealId, formData) => request(`/deals/${dealId}/conversations`, {
    method: 'POST',
    body: formData,
  }),
  analyzeConversation: (dealId) => request(`/deals/${dealId}/analyze`, {
    method: 'POST',
  }),
  getLatestAnalysis: (dealId) => request(`/deals/${dealId}/analyses/latest`),

  // Legal Bonds & AI Detection
  getBonds: (dealId) => request(`/deals/${dealId}/bonds`),
  uploadBond: (dealId, formData) => request(`/deals/${dealId}/bonds`, {
    method: 'POST',
    body: formData,
  }),
  deleteBond: (dealId, bondId) => request(`/deals/${dealId}/bonds/${bondId}`, {
    method: 'DELETE',
  }),
  applyBondToAgreement: (dealId, bondId) => request(`/deals/${dealId}/bonds/${bondId}/apply-to-agreement`, {
    method: 'POST',
  }),

  // Clarifications
  getClarifications: (dealId) => request(`/deals/${dealId}/clarifications`),
  submitClarification: (dealId, payload) => request(`/deals/${dealId}/clarifications`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateClarification: (clarificationId, answer) => request(`/clarifications/${clarificationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ answer }),
  }),

  // Agreements & Approvals
  getAgreements: (dealId) => request(`/deals/${dealId}/agreements`),
  getAgreement: (versionId) => request(`/agreements/${versionId}`),
  createAgreement: (dealId, payload) => request(`/deals/${dealId}/agreements`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  editAgreement: (versionId, payload) => request(`/agreements/${versionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  }),
  requestReview: (versionId) => request(`/agreements/${versionId}/request-review`, {
    method: 'POST',
  }),
  approveAgreement: (versionId, payload) => request(`/agreements/${versionId}/approve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  requestChanges: (versionId, payload) => request(`/agreements/${versionId}/request-changes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  addComment: (versionId, payload) => request(`/agreements/${versionId}/comments`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  downloadPdf: async (versionId, filename = 'Agreement.pdf') => {
    const blob = await request(`/agreements/${versionId}/pdf`);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },

  // Amendments
  getAmendments: (dealId) => request(`/deals/${dealId}/amendments`),
  proposeAmendment: (dealId, payload) => request(`/deals/${dealId}/amendments`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // Activity Log & Tamper-Evident Verification
  getActivity: (dealId) => request(`/deals/${dealId}/activity`),
  verifyActivityChain: (dealId) => request(`/deals/${dealId}/activity/verify`),

  // Notifications
  getNotifications: () => request('/notifications'),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, {
    method: 'PATCH',
  }),
  markAllNotificationsRead: () => request('/notifications/read-all', {
    method: 'POST',
  }),
};
