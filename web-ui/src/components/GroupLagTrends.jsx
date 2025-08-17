import React from 'react';
import { Paper, Typography, Stack, Chip } from '@mui/material';

/** very small inline SVG sparkline */
function Spark({ series = [], height = 28 }) {
  const width = Math.max(80, series.length * 4);
  if (!series.length) return <svg width={width} height={height} />;
  const max = Math.max(...series, 1);
  const pts = series.map((v, i) => {
    const x = (i / (series.length - 1)) * (width - 6) + 3;
    const y = height - 3 - (v / max) * (height - 6);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={width} height={height}>
      <polyline fill="none" stroke="currentColor" strokeWidth="1.5" points={pts} />
    </svg>
  );
}

export default function GroupLagTrends({ history = [] }) {
  // Build per-partition series of lag values
  const byPartition = React.useMemo(() => {
    const map = new Map();
    history.forEach(snap => {
      snap.parts.forEach(p => {
        const arr = map.get(p.partition) ?? [];
        arr.push(typeof p.lag === 'number' ? p.lag : 0);
        map.set(p.partition, arr);
      });
    });
    return Array.from(map.entries()).sort((a,b) => a[0]-b[0]);
  }, [history]);

  const count = history.length;

  return (
    <Paper variant="outlined" sx={{ p:2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1">Trends</Typography>
        <Chip size="small" label={`${count} samples`} />
      </Stack>
      {!count && <Typography variant="body2">Start auto-refresh to see trends.</Typography>}
      <Stack spacing={1}>
        {byPartition.map(([pid, series]) => (
          <Stack key={pid} direction="row" spacing={2} alignItems="center">
            <Typography variant="caption" sx={{ width: 48 }}>P#{pid}</Typography>
            <Spark series={series} />
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}
