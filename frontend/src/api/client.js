import axios from 'axios';

const client = axios.create({ baseURL: '/api' });

// Attach token from localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('airrule_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear token
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('airrule_token');
      localStorage.removeItem('airrule_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──
export const authApi = {
  login: (username, password) =>
    client.post('/auth/login', { username, password }).then((r) => r.data),
  me: () => client.get('/auth/me').then((r) => r.data),
};

// ── Broadcasters ──
export const broadcasterApi = {
  list: () => client.get('/broadcasters').then((r) => r.data),
};

// ── Policies ──
export const policyApi = {
  list: () => client.get('/policies').then((r) => r.data),
  get: (id) => client.get(`/policies/${id}`).then((r) => r.data),
  create: (data) => client.post('/policies', data).then((r) => r.data),
  update: (id, data) => client.put(`/policies/${id}`, data).then((r) => r.data),
  delete: (id) => client.delete(`/policies/${id}`).then((r) => r.data),
  history: (id) => client.get(`/policies/${id}/history`).then((r) => r.data),
};

// ── Tech Items ──
export const techItemApi = {
  list: () => client.get('/tech-items').then((r) => r.data),
  get: (id) => client.get(`/tech-items/${id}`).then((r) => r.data),
  create: (data) => client.post('/tech-items', data).then((r) => r.data),
  update: (id, data) => client.put(`/tech-items/${id}`, data).then((r) => r.data),
  history: (id) => client.get(`/tech-items/${id}/history`).then((r) => r.data),
};

// ── Mappings ──
export const mappingApi = {
  get: (broadcasterId) => client.get(`/mappings/${broadcasterId}`).then((r) => r.data),
  update: (broadcasterId, itemIds) =>
    client.put(`/mappings/${broadcasterId}`, { item_ids: itemIds }).then((r) => r.data),
};

// ── History ──
export const historyApi = {
  all: () => client.get('/history').then((r) => r.data),
};

// ── Test Pipeline ──
export const testApi = {
  run: (srt_text, broadcaster_id, pipeline, params_override = {}) =>
    client.post('/test/run', { srt_text, broadcaster_id, pipeline, params_override }).then((r) => r.data),
};

export default client;
