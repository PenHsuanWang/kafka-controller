import { apiGet } from './client';

export const getByOffset = (topic, partition, offset, limit = 50) =>
  apiGet('/messages/by-offset', { topic, partition, offset, limit });

export const getFromTimestamp = (topic, partition, tsIso, limit = 50) =>
  apiGet('/messages/from-timestamp', { topic, partition, ts: tsIso, limit });
