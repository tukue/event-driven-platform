export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  orders: '/api/orders',
  delivery: (orderId) => `/api/orders/${orderId}/delivery`,
  state: '/api/state',
  eventsBatch: '/api/events/batch',
};
