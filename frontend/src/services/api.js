import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000,
});

export const checkHealth = () => api.get('/health');

export const processEmail = (emailText, threadId) =>
  api.post('/process', { 
    email_text: emailText,
    thread_id: threadId 
  });

export default api;
