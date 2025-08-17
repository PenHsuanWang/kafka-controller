// src/api/monitoring.js
const BASE = "/api/v1/monitoring";

export async function getSnapshot(groupId, topic) {
  const r = await fetch(`${BASE}/groups/${encodeURIComponent(groupId)}/snapshot?topic=${encodeURIComponent(topic)}`);
  if (!r.ok) throw new Error(`Snapshot failed: ${r.status}`);
  return r.json();
}

export async function getRates(groupId, topic, windowSec = 60) {
  const r = await fetch(
    `${BASE}/groups/${encodeURIComponent(groupId)}/rates?topic=${encodeURIComponent(topic)}&windowSec=${windowSec}`
  );
  if (!r.ok) throw new Error(`Rates failed: ${r.status}`);
  return r.json();
}
