import { apiGet } from './client';

/**
 * List all topic names (supports optional substring filter `q`)
 * - Kept the same signature so existing code is unaffected.
 */
export const listTopics = (q) =>
  apiGet('/topics', (typeof q === 'string' && q.trim()) ? { q: q.trim() } : undefined);

export const getTopic = (topic) =>
  apiGet(`/topics/${encodeURIComponent(topic)}`);

export const fetchMessagesForTopic = (topic, { partition, offset, timestamp, limit } = {}) =>
  apiGet(`/topics/${encodeURIComponent(topic)}/messages`, {
    partition,
    offset,
    timestamp,
    limit,
  });
