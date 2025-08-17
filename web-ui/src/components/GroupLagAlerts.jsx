import React from 'react';
import { Paper, Stack, TextField, Typography, Button } from '@mui/material';
import { enqueueSnackbar } from 'notistack';
import useLocalStorage from '../hooks/useLocalStorage';

export default function GroupLagAlerts({ parts = [] }) {
  const [cfg, setCfg] = useLocalStorage('alerts.groups', { maxLag: 1000, timeLagSec: 300 });
  React.useEffect(() => {
    if (!parts?.length) return;
    const breached = [];
    const maxLag = Math.max(...parts.map(p => p.lag ?? 0));
    if (cfg.maxLag && maxLag >= cfg.maxLag) breached.push(`Max lag >= ${cfg.maxLag}`);
    const maxTimeLag = Math.max(...parts.map(p => p.timeLagSec ?? 0));
    if (cfg.timeLagSec && maxTimeLag >= cfg.timeLagSec) breached.push(`Time lag >= ${cfg.timeLagSec}s`);
    if (breached.length) {
      enqueueSnackbar(`Alerts: ${breached.join('; ')}`, { variant: 'warning' });
    }
  }, [parts, cfg]);

  return (
    <Paper variant="outlined" sx={{ p:2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>Local Alerts (client only)</Typography>
      <Stack direction="row" spacing={2}>
        <TextField
          label="Max lag threshold"
          type="number" size="small"
          value={cfg.maxLag}
          onChange={e => setCfg({ ...cfg, maxLag: Number(e.target.value) || 0 })}
        />
        <TextField
          label="Time lag threshold (sec)"
          type="number" size="small"
          value={cfg.timeLagSec}
          onChange={e => setCfg({ ...cfg, timeLagSec: Number(e.target.value) || 0 })}
        />
        <Button variant="outlined" onClick={() => setCfg({ maxLag: 1000, timeLagSec: 300 })}>Reset</Button>
      </Stack>
    </Paper>
  );
}
