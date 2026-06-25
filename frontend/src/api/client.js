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

// ── Policies (matrix structure) ──
export const policyApi = {
  // 전체 매트릭스 트리 (카테고리 → 항목 → 셀값)
  matrix: () => client.get('/policies').then((r) => r.data),

  // 셀 값 upsert (item_id + broadcaster_id) — 변경 시 이력 자동 기록
  upsertValue: (data) => client.put('/policies/values', data).then((r) => r.data),
  valueHistory: (valueId) => client.get(`/policies/values/${valueId}/history`).then((r) => r.data),

  // 전체 정책 변경 이력
  history: () => client.get('/policies/history').then((r) => r.data),

  // 카테고리 CRUD
  createCategory: (data) => client.post('/policies/categories', data).then((r) => r.data),
  updateCategory: (id, data) => client.put(`/policies/categories/${id}`, data).then((r) => r.data),
  deleteCategory: (id) => client.delete(`/policies/categories/${id}`).then((r) => r.data),

  // 항목 CRUD
  createItem: (data) => client.post('/policies/items', data).then((r) => r.data),
  updateItem: (id, data) => client.put(`/policies/items/${id}`, data).then((r) => r.data),
  deleteItem: (id) => client.delete(`/policies/items/${id}`).then((r) => r.data),
};

// ── Tech Items ──
export const techItemApi = {
  list: () => client.get('/tech-items').then((r) => r.data),
  get: (id) => client.get(`/tech-items/${id}`).then((r) => r.data),
  create: (data) => client.post('/tech-items', data).then((r) => r.data),
  update: (id, data) => client.put(`/tech-items/${id}`, data).then((r) => r.data),
  history: (id) => client.get(`/tech-items/${id}/history`).then((r) => r.data),
};

// ── Item ↔ Tech links (연결 찾기) ──
export const linkApi = {
  all: () => client.get('/links').then((r) => r.data),
  byPolicyItem: (id) => client.get(`/links/by-policy-item/${id}`).then((r) => r.data),
  byTechItem: (id) => client.get(`/links/by-tech-item/${id}`).then((r) => r.data),
  create: (data) => client.post('/links', data).then((r) => r.data),
  remove: (id) => client.delete(`/links/${id}`).then((r) => r.data),
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