import { apiGet } from './client';

export const getClusterSnapshot = () => apiGet('/cluster');
