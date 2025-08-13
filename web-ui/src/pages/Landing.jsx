import React from 'react';
import { Typography, Paper } from '@mui/material';
export default function Landing() {
  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h5">Landing (E2E Freshness)</Typography>
      <Typography variant="body2">Coming soon: pipelines list, watermark & backfill.</Typography>
    </Paper>
  );
}
