// src/utils/base64.js

/**
 * Minimal UTF-8 byte array → JS string decoder for environments
 * without TextDecoder. Correctly handles 1–4 byte sequences.
 */
function utf8BytesToString(bytes) {
  let out = '';
  for (let i = 0; i < bytes.length; ) {
    const b0 = bytes[i++];

    if (b0 < 0x80) {
      out += String.fromCharCode(b0);
      continue;
    }

    if ((b0 & 0xe0) === 0xc0) {
      const b1 = bytes[i++];
      out += String.fromCharCode(((b0 & 0x1f) << 6) | (b1 & 0x3f));
      continue;
    }

    if ((b0 & 0xf0) === 0xe0) {
      const b1 = bytes[i++];
      const b2 = bytes[i++];
      out += String.fromCharCode(
        ((b0 & 0x0f) << 12) | ((b1 & 0x3f) << 6) | (b2 & 0x3f)
      );
      continue;
    }

    // 4-byte sequence → surrogate pair
    const b1 = bytes[i++];
    const b2 = bytes[i++];
    const b3 = bytes[i++];
    let codePoint =
      ((b0 & 0x07) << 18) |
      ((b1 & 0x3f) << 12) |
      ((b2 & 0x3f) << 6) |
      (b3 & 0x3f);
    codePoint -= 0x10000;
    out += String.fromCharCode(
      0xd800 + (codePoint >> 10),
      0xdc00 + (codePoint & 0x3ff)
    );
  }
  return out;
}

/** Normalize Base64URL to classic Base64 (and fix padding). */
function normalizeBase64(b64) {
  let s = String(b64).replace(/-/g, '+').replace(/_/g, '/');
  const pad = s.length % 4;
  if (pad) s += '='.repeat(4 - pad);
  return s;
}

/**
 * Decode a Base64 string to a UTF-8 string.
 * @param {string} b64
 * @returns {string}
 */
export function decodeBase64Utf8(b64) {
  if (b64 == null) return '';
  const normalized = normalizeBase64(b64);

  // Prefer Node.js Buffer when available.
  if (typeof Buffer !== 'undefined' && typeof Buffer.from === 'function') {
    try {
      return Buffer.from(normalized, 'base64').toString('utf8');
    } catch {
      // fall through
    }
  }

  // Browser path using window.atob if available.
  const atobFn =
    typeof window !== 'undefined' && typeof window.atob === 'function'
      ? window.atob
      : null;

  if (atobFn) {
    try {
      const binary = atobFn(normalized); // base64 -> binary (latin1)
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
      }

      if (typeof TextDecoder !== 'undefined') {
        try {
          return new TextDecoder('utf-8', { fatal: false }).decode(bytes);
        } catch {
          // fallback to manual UTF-8 decode below
        }
      }
      return utf8BytesToString(bytes);
    } catch {
      // fall through
    }
  }

  // As a last resort, return empty to keep UI resilient.
  return '';
}

/**
 * Convenience helper: tries to decode and falls back to the original text
 * when decoding produces an empty string.
 */
export function safeDecodeBase64Utf8(b64OrText) {
  const decoded = decodeBase64Utf8(b64OrText);
  return decoded || String(b64OrText ?? '');
}

export default decodeBase64Utf8;