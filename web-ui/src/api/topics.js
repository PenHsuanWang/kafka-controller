import { apiGet } from './client';

export const listTopics = () => apiGet('/topics');
export const getTopic = (topic) => apiGet(`/topics/${encodeURIComponent(topic)}`);
