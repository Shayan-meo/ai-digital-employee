import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
});

export const fetchHealth = () => api.get('/health').then(r => r.data);
export const fetchDashboardStats = () => api.get('/dashboard-stats').then(r => r.data);
export const fetchProducts = () => api.get('/products').then(r => r.data);
export const fetchPartners = () => api.get('/partners').then(r => r.data);
export const fetchInvoices = () => api.get('/invoices').then(r => r.data);
export const fetchCategories = () => api.get('/categories').then(r => r.data);
export const fetchAccountingSummary = () => api.get('/accounting/summary').then(r => r.data);

// WhatsApp
export const sendWhatsApp = (phone, message) => api.post('/whatsapp/send', { phone, message }).then(r => r.data);
export const fetchWhatsAppStatus = (jobId) => api.get(`/whatsapp/status/${jobId}`).then(r => r.data);
export const fetchWhatsAppHistory = () => api.get('/whatsapp/history').then(r => r.data);
export const clearWhatsAppHistory = () => api.post('/whatsapp/clear-history').then(r => r.data);

// Gmail
export const fetchGmailUnread = () => api.get('/gmail/unread').then(r => r.data);
export const fetchGmailLatest = () => api.get('/gmail/latest').then(r => r.data);
export const sendGmail = (to, subject, message) => api.post('/gmail/send', { to, subject, message }, { timeout: 75000 }).then(r => r.data);
export const replyGmail = (to, subject, message, threadId, messageId) =>
  api.post('/gmail/reply', { to, subject, message, threadId, messageId }, { timeout: 75000 }).then(r => r.data);

// Social Media Hub
export const postSocial = (formData) => api.post('/social/post', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 300000,  // 5 min — Playwright browsers take time
}).then(r => r.data);

export default api;
