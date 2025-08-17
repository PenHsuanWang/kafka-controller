export function toSecondsBetween(isoA, isoB) {
  if (!isoA || !isoB) return undefined;
  try {
    const a = Date.parse(isoA);
    const b = Date.parse(isoB);
    if (!Number.isFinite(a) || !Number.isFinite(b)) return undefined;
    return Math.max(0, Math.round((a - b) / 1000));
  } catch {
    return undefined;
  }
}

export function computeKpis(parts = []) {
  const totalLag = parts.reduce((acc, p) => acc + (typeof p.lag === 'number' ? p.lag : 0), 0);
  const max = parts.reduce((acc, p) => (typeof p.lag === 'number' && p.lag > (acc?.lag ?? -1) ? p : acc), null);
  const tlags = parts.map(p => p.timeLagSec).filter(v => Number.isFinite(v)).sort((a,b) => a-b);
  const p95 = tlags.length ? tlags[Math.floor(0.95 * (tlags.length - 1))] : undefined;
  return {
    totalLag,
    maxLag: max?.lag ?? 0,
    maxLagPartition: max?.partition,
    timeLagP95Sec: p95,
    partitions: parts.length,
  };
}
