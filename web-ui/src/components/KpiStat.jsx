import React from 'react';
import { Card, CardContent, Typography } from '@mui/material';

export default function KpiStat({ label, value }) {
  return (
    <Card sx={{ minWidth: 200 }}>
      <CardContent>
        <Typography color="text.secondary" gutterBottom>{label}</Typography>
        <Typography variant="h4">{value}</Typography>
      </CardContent>
    </Card>
  );
}
