function readLocal(key) {
  try {
    const v = localStorage.getItem(key);
    return v ? JSON.parse(v) : null;
  } catch {
    return null;
  }
}

function getApiBase() {
  return readLocal('apiBase') || process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';
}

export async function apiGet(path, params) {
  const API_BASE = getApiBase();
  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const r = await fetch(url.toString(), { headers: { 'Accept': 'application/json' } });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export async function apiPost(path, params) {
  const API_BASE = getApiBase();
  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const r = await fetch(url.toString(), { method: 'POST' });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
