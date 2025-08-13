import React from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { getGroupLag, previewReset, applyReset } from '../api/groups';
import { Paper, Stack, Typography, TextField, Button, Table, TableHead, TableRow, TableCell, TableBody, Divider, Chip, Box, MenuItem, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import { enqueueSnackbar } from 'notistack';
import { toIsoUtcZ, fmtIsoShort } from '../utils/datetime';

export default function Groups() {
  const [groupId, setGroupId] = React.useState('demo-group');
  const [topic, setTopic] = React.useState('demo');
  const [auto, setAuto] = React.useState(false);
  const [tsLocal, setTsLocal] = React.useState('');
  const [partitionsSel, setPartitionsSel] = React.useState(undefined);

  const query = useQuery({
    queryKey: ['lag', groupId, topic],
    queryFn: () => getGroupLag(groupId, topic),
    enabled: !!groupId && !!topic,
    refetchInterval: auto ? 10000 : false,
  });

  const [preview, setPreview] = React.useState(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  const doPreview = useMutation({
    mutationFn: async () => {
      const iso = tsLocal.includes('T') ? toIsoUtcZ(tsLocal) : tsLocal; // also accept raw ISO
      const res = await previewReset(groupId, topic, iso, partitionsSel);
      setPreview(res.targets);
      enqueueSnackbar('Preview ready', { variant: 'info' });
    }
  });

  const doApply = useMutation({
    mutationFn: async () => {
      const iso = tsLocal.includes('T') ? toIsoUtcZ(tsLocal) : tsLocal;
      const res = await applyReset(groupId, topic, iso, partitionsSel);
      enqueueSnackbar('Offsets reset applied', { variant: 'success' });
      setConfirmOpen(false);
      setPreview(null);
      query.refetch();
      return res;
    }
  });

  const parts = query.data?.partitions ?? [];
  const allPartitionIds = parts.map(p => p.partition);

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Consumer Groups</Typography>
      <Paper sx={{ p:2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField label="Group ID" value={groupId} onChange={e => setGroupId(e.target.value)} size="small" />
          <TextField label="Topic" value={topic} onChange={e => setTopic(e.target.value)} size="small" />
          <Button variant="contained" onClick={() => query.refetch()}>Load</Button>
          <Button variant={auto ? 'contained' : 'outlined'} onClick={() => setAuto(v => !v)}>Auto 10s</Button>
        </Stack>
      </Paper>

      {query.data && (
        <Paper sx={{ p:2 }}>
          <Typography variant="subtitle1">Partitions (Lag & Drift)</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Committed / End</TableCell>
                <TableCell>Lag</TableCell>
                <TableCell>End TS</TableCell>
                <TableCell>LastRec TS</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {parts.map(p => (
                <TableRow key={p.partition}>
                  <TableCell>{p.partition}</TableCell>
                  <TableCell>{p.committedOffset ?? '-'} / {p.endOffset}</TableCell>
                  <TableCell>
                    {p.lag ?? '-'}{' '}
                    {p.lag ? (
                      <Chip
                        size="small"
                        color={p.lag >= 1000 ? 'error' : p.lag > 0 ? 'warning' : 'default'}
                        label={p.lag >= 1000 ? 'high' : p.lag > 0 ? 'low' : 'ok'}
                      />
                    ) : null}
                  </TableCell>
                  <TableCell>{fmtIsoShort(p.endOffsetTimestamp)}</TableCell>
                  <TableCell>{fmtIsoShort(p.lastRecordTimestamp)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Divider sx={{ my:2 }} />

          <Stack spacing={2}>
            <Typography variant="subtitle1">Reset Offsets (by Timestamp)</Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                label="Timestamp"
                type="datetime-local"
                value={tsLocal}
                onChange={(e) => setTsLocal(e.target.value)}
                size="small"
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                select size="small"
                label="Partitions"
                value={(partitionsSel ?? allPartitionIds).join(',')}
                onChange={(e) => {
                  const v = e.target.value;
                  const arr = v === '' ? undefined : v.split(',').map(n => Number(n));
                  setPartitionsSel(arr);
                }}
                helperText="Comma-separated list (empty = all)"
                sx={{ minWidth: 240 }}
              >
                <MenuItem value={allPartitionIds.join(',')}>All</MenuItem>
                {allPartitionIds.map(id => (
                  <MenuItem key={id} value={String(id)}>{id}</MenuItem>
                ))}
              </TextField>
              <Button variant="outlined" onClick={() => doPreview.mutate()} disabled={!tsLocal || doPreview.isPending}>Preview</Button>
              <Button variant="contained" color="error" onClick={() => setConfirmOpen(true)} disabled={!preview}>Confirm Apply</Button>
            </Stack>

            {preview && (
              <Box>
                <Typography variant="body2" sx={{ mb: 1 }}>Preview result:</Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Partition</TableCell>
                      <TableCell>Current</TableCell>
                      <TableCell>Target</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(preview).map(([pid, off]) => (
                      <TableRow key={pid}>
                        <TableCell>{pid}</TableCell>
                        <TableCell>{parts.find(p => p.partition === Number(pid))?.committedOffset ?? '-'}</TableCell>
                        <TableCell>{off ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
          </Stack>
        </Paper>
      )}

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Confirm offset reset</DialogTitle>
        <DialogContent dividers>
          This will move <b>{groupId}</b> on topic <b>{topic}</b> to the previewed offsets for timestamp
          <b> {tsLocal ? toIsoUtcZ(tsLocal) : ''}</b>. Ensure consumers are idle.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button onClick={() => doApply.mutate()} color="error" variant="contained" disabled={!preview || doApply.isPending}>Apply</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
