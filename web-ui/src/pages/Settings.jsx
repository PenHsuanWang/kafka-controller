import React from 'react';
import { Paper, Stack, Typography, TextField, Button } from '@mui/material';
import useLocalStorage from '../hooks/useLocalStorage';

export default function Settings() {
  const [apiBase, setApiBase] = useLocalStorage('apiBase', process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1');
  const [wsUrl, setWsUrl] = useLocalStorage('wsUrl', process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/v1/stream');

  const apply = () => {
    // Values persisted already; reload to re-init API/WS providers.
    window.location.reload();
  };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Settings</Typography>
      <Paper sx={{ p:2 }}>
        <Stack spacing={2}>
          <TextField label="API Base" value={apiBase} onChange={e => setApiBase(e.target.value)} fullWidth />
          <TextField label="WebSocket URL" value={wsUrl} onChange={e => setWsUrl(e.target.value)} fullWidth />
          <Button variant="contained" onClick={apply}>Save & Reload</Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
