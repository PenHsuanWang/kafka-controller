import React from 'react';

/**
 * Keeps a bounded history of group lag snapshots in-memory for Trends.
 * Stores arrays keyed by (groupId, topic).
 */
export default function useLagHistory({ groupId, topic, sample, enabled, capacity = 60 }) {
  const key = `${groupId}::${topic}`;
  const storeRef = React.useRef(new Map()); // key -> array

  const history = React.useMemo(() => {
    const arr = storeRef.current.get(key);
    return Array.isArray(arr) ? arr : [];
  }, [key, sample]); // re-evaluate on new sample so components update

  React.useEffect(() => {
    if (!enabled || !sample) return;
    const arr = storeRef.current.get(key) ?? [];
    arr.push({ ts: Date.now(), parts: sample });
    while (arr.length > capacity) arr.shift();
    storeRef.current.set(key, arr);
  }, [enabled, capacity, key, sample]);

  const clear = React.useCallback(() => {
    storeRef.current.delete(key);
  }, [key]);

  return { history, clear };
}
