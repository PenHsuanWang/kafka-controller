import React from 'react';
import { Box, Stack, Typography } from '@mui/material';

// Small viridis-like palette; we’ll interpolate between these.
const VIRIDIS = [
  '#440154', '#482173', '#3e4989', '#31688e', '#26828e',
  '#1f9e89', '#35b779', '#6ece58', '#b8de29', '#fde725'
];

function hexToRgb(hex) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return m ? { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) } : { r:0,g:0,b:0 };
}
function rgbToHex({ r, g, b }) {
  const toHex = (v) => v.toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
function lerp(a, b, t) { return a + (b - a) * t; }
function lerpColor(hex1, hex2, t) {
  const c1 = hexToRgb(hex1), c2 = hexToRgb(hex2);
  return rgbToHex({
    r: Math.round(lerp(c1.r, c2.r, t)),
    g: Math.round(lerp(c1.g, c2.g, t)),
    b: Math.round(lerp(c1.b, c2.b, t)),
  });
}
function viridis(t) {
  if (t <= 0) return VIRIDIS[0];
  if (t >= 1) return VIRIDIS[VIRIDIS.length - 1];
  const pos = t * (VIRIDIS.length - 1);
  const i = Math.floor(pos);
  const frac = pos - i;
  return lerpColor(VIRIDIS[i], VIRIDIS[i + 1], frac);
}

function fmtShort(ms) {
  const d = new Date(ms);
  // 12:34:56 or mm:ss if the window is small
  return d.toISOString().split('T')[1].replace('Z','').slice(0,8);
}

/**
 * HeatStrip
 * props:
 *  - timestampsMs: number[]  (epoch ms)
 *  - bins: number            (default 60)
 *  - height: number          (px, default 22)
 *  - startMs?: number        (optional domain start; default min(timestamps))
 *  - endMs?: number          (optional domain end; default max(timestamps))
 *  - showLegend?: boolean    (default true)
 */
export default function HeatStrip({
  timestampsMs,
  bins = 60,
  height = 22,
  startMs,
  endMs,
  showLegend = true,
}) {
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const cssW = canvas.clientWidth || 600;
    const cssH = height;
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // guard: no data
    if (!timestampsMs || timestampsMs.length === 0) {
      ctx.clearRect(0, 0, cssW, cssH);
      ctx.fillStyle = '#eee';
      ctx.fillRect(0, 0, cssW, cssH);
      ctx.fillStyle = '#666';
      ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, sans-serif';
      ctx.fillText('No data', 8, cssH - 6);
      return;
    }

    const lo = startMs ?? Math.min(...timestampsMs);
    let hi = endMs ?? Math.max(...timestampsMs);
    if (hi <= lo) hi = lo + 1; // avoid divide-by-zero

    const binWidth = (hi - lo) / bins;
    const counts = new Array(bins).fill(0);
    for (const t of timestampsMs) {
      if (t < lo || t > hi) continue;
      let idx = Math.floor((t - lo) / binWidth);
      if (idx >= bins) idx = bins - 1;
      if (idx < 0) idx = 0;
      counts[idx]++;
    }
    const maxCount = Math.max(1, ...counts);

    const colW = cssW / bins;
    ctx.clearRect(0, 0, cssW, cssH);
    for (let i = 0; i < bins; i++) {
      const v = counts[i] / maxCount; // 0..1
      const color = v === 0 ? '#f5f5f5' : viridis(v);
      ctx.fillStyle = color;
      ctx.fillRect(i * colW, 0, Math.ceil(colW) + 1, cssH);
    }

    // thin border
    ctx.strokeStyle = '#ddd';
    ctx.strokeRect(0.5, 0.5, cssW - 1, cssH - 1);
  }, [timestampsMs, bins, height, startMs, endMs]);

  const lo = (startMs ?? (timestampsMs?.length ? Math.min(...timestampsMs) : undefined));
  const hi = (endMs ?? (timestampsMs?.length ? Math.max(...timestampsMs) : undefined));

  return (
    <Stack spacing={0.5}>
      <Box
        component="canvas"
        ref={canvasRef}
        sx={{ width: '100%', height, borderRadius: 1, display: 'block' }}
      />
      {showLegend && lo != null && hi != null && (
        <Stack direction="row" justifyContent="space-between">
          <Typography variant="caption" color="text.secondary">{fmtShort(lo)}</Typography>
          <Typography variant="caption" color="text.secondary">{fmtShort(hi)}</Typography>
        </Stack>
      )}
    </Stack>
  );
}
