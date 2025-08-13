import React from 'react';
import { Grid, Alert, Stack, Typography } from '@mui/material';
import KpiStat from '../components/KpiStat';
import { WsContext } from '../ws/WsProvider';
import { useQuery } from '@tanstack/react-query';
import { getClusterSnapshot } from '../api/cluster';

export default function Dashboard() {
  const { kpis, connected } = React.useContext(WsContext);
  const snap = useQuery({ queryKey: ['cluster'], queryFn: getClusterSnapshot, enabled: !connected, refetchInterval: 5000 });
  const data = kpis ?? snap.data;

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Dashboard</Typography>
      {!connected && <Alert severity="info">WebSocket not connected – showing snapshot.</Alert>}
      {data ? (
        <>
          <Grid container spacing={2}>
            <Grid item><KpiStat label="Brokers Online" value={data.brokersOnline} /></Grid>
            <Grid item><KpiStat label="URPs" value={data.underReplicatedPartitions} /></Grid>
            <Grid item><KpiStat label="Active Controller" value={data.activeControllerCount} /></Grid>
          </Grid>
          <Grid container spacing={2}>
            <Grid item><KpiStat label="Bytes In /s" value={data.throughput.bytesInPerSec.toFixed(0)} /></Grid>
            <Grid item><KpiStat label="Bytes Out /s" value={data.throughput.bytesOutPerSec.toFixed(0)} /></Grid>
            <Grid item><KpiStat label="Messages In /s" value={data.throughput.messagesInPerSec.toFixed(0)} /></Grid>
          </Grid>
        </>
      ) : (
        <Alert severity="warning">No KPI data yet.</Alert>
      )}
    </Stack>
  );
}
