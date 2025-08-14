import { apiGet, apiPost } from './client';

export const getGroupLag = (groupId, topic) =>
  apiGet(`/consumer-groups/${encodeURIComponent(groupId)}/lag`, { topic });

export const previewReset = (groupId, topic, timestamp, partitions) =>
  apiPost(`/consumer-groups/${encodeURIComponent(groupId)}:reset-by-timestamp`, { topic, timestamp, dry_run: true, partitions });

export const applyReset = (groupId, topic, timestamp, partitions) =>
  apiPost(`/consumer-groups/${encodeURIComponent(groupId)}:reset-by-timestamp`, { topic, timestamp, dry_run: false, partitions });

export const listConsumerGroups = (q) =>
  apiGet('/consumer-groups', q ? { q } : undefined);
