export function b64ToUtf8(b64) {
  if (!b64) return undefined;
  try {
    const bin = atob(b64);
    // Try to display as UTF-8; if not valid, show hex length fallback
    return decodeURIComponent(Array.prototype.map.call(bin, (c) =>
      '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    ).join(''));
  } catch {
    return undefined;
  }
}
