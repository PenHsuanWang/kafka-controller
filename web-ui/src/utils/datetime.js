// Format an ISO/timestamp-ish input as "YYYY-MM-DD HH:mm:ss" (local timezone rendering of a UTC instant).
export function fmtIsoShort(v) {
  if (v == null || v === '') return '';
  let ms;
  if (v instanceof Date) {
    ms = v.getTime();
  } else if (typeof v === 'number') {
    ms = v;
  } else {
    const parsed = Date.parse(String(v));
    if (!Number.isFinite(parsed)) return '';
    ms = parsed;
  }
  const d = new Date(ms);
  const iso = d.toISOString(); // always UTC with Z
  return iso.replace('T', ' ').replace('Z', '').slice(0, 19);
}

// Parse local-naive strings like "2024-08-02T12:34(:56(.123)?)?" or "2024-08-02".
function parseNaiveLocalToDate(s) {
  const m = String(s).trim().match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?)?$/
  );
  if (!m) return new Date(s); // fall back to native parsing
  const [, y, mo, d, hh = '0', mm = '0', ss = '0', ms = '0'] = m;
  return new Date(
    Number(y),
    Number(mo) - 1,
    Number(d),
    Number(hh),
    Number(mm),
    Number(ss),
    Number(String(ms).padEnd(3, '0'))
  );
}

/**
 * Convert various timestamp inputs to a canonical ISO string in UTC with trailing 'Z'.
 * - Numbers are treated as epoch ms.
 * - ISO with 'Z' or explicit offset are respected (idempotent).
 * - Local-naive inputs from <input type="datetime-local"> like "2024-08-02T12:34"
 *   are interpreted in the user's local timezone and converted to UTC.
 * Returns '' for falsy/invalid inputs.
 */
export function toIsoUtcZ(v) {
  if (v == null || v === '') return '';
  if (v instanceof Date) return new Date(v.getTime()).toISOString();
  if (typeof v === 'number') return new Date(v).toISOString();

  const s = String(v).trim();
  // If it already has a timezone (Z or ±hh:mm or ±hhmm), rely on native parse
  const hasExplicitTz = /[zZ]$|[+\-]\d{2}:?\d{2}$/.test(s);
  let d;
  if (hasExplicitTz) {
    const ms = Date.parse(s);
    if (!Number.isFinite(ms)) return '';
    d = new Date(ms);
  } else {
    d = parseNaiveLocalToDate(s);
  }
  return Number.isFinite(d.getTime()) ? d.toISOString() : '';
}