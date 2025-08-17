import React from 'react';
import { Stack } from '@mui/material';
import KpiStat from './KpiStat';
import { computeKpis } from '../utils/lag';

export default function GroupLagKpis({ parts = [] }) {
  const k = React.useMemo(() => computeKpis(parts), [parts]);

  return (
    <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap' }}>
      <KpiStat label="Total Lag" value={k.totalLag.toLocaleString()} hint={`${k.partitions} partitions`} />
      <KpiStat label="Max Lag" value={k.maxLag?.toLocaleString?.() ?? k.maxLag} hint={`P#${k.maxLagPartition ?? '-'}`} />
      <KpiStat label="Time Lag p95" value={k.timeLagP95Sec != null ? `${k.timeLagP95Sec}s` : '—'} hint="Head vs last record" />
    </Stack>
  );
}
