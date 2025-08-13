export function toIsoUtcZ(localDateTime) {
  // Accepts input from <input type="datetime-local"> => "YYYY-MM-DDTHH:mm"
  // Returns ISO "YYYY-MM-DDTHH:mm:ssZ"
  if (!localDateTime) return '';
  const d = new Date(localDateTime);
  return new Date(Date.UTC(
    d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes(), 0
  )).toISOString().replace('.000Z', 'Z');
}

export function fmtIsoShort(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toISOString().replace('.000Z', 'Z');
  } catch {
    return String(iso);
  }
}
