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

  const r = await fetch(url.toString(), {
    mode: 'cors',
    headers: { 'Accept': 'application/json' },
  });

  const text = await r.text();
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const j = JSON.parse(text);
      if (j && j.detail) msg += ` - ${j.detail}`;
    } catch {}
    throw new Error(msg);
  }
  return text ? JSON.parse(text) : null;
}

export async function apiPost(path, params) {
  const API_BASE = getApiBase();
  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, String(v)));

  const r = await fetch(url.toString(), {
    mode: 'cors',
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  const text = await r.text();
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const j = JSON.parse(text);
      if (j && j.detail) msg += ` - ${j.detail}`;
    } catch {}
    throw new Error(msg);
  }
  return text ? JSON.parse(text) : null;
}
