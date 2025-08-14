import React from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Paper, Stack, Typography, TextField, Button, Table, TableHead, TableRow,
  TableCell, TableBody, Divider, Chip, Box, MenuItem, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert, CircularProgress, Autocomplete
} from '@mui/material';
import { enqueueSnackbar } from 'notistack';
import { getGroupLag, previewReset, applyReset, listConsumerGroups } from '../api/groups';
import { listTopics } from '../api/topics';
import { toIsoUtcZ, fmtIsoShort } from '../utils/datetime';

export default function Groups() {
  // ----- selections -----
  const [groupId, setGroupId] = React.useState('demo-group');
  const [groupInput, setGroupInput] = React.useState('demo-group');
  const [topic, setTopic] = React.useState('demo');
  const [topicInput, setTopicInput] = React.useState('demo');

  const [auto, setAuto] = React.useState(false);
  const [tsLocal, setTsLocal] = React.useState('');
  const [partitionsSel, setPartitionsSel] = React.useState(undefined);

  // ----- options -----
  const groupsQuery = useQuery({
    queryKey: ['consumer-groups'],
    queryFn: () => listConsumerGroups(),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const topicsQuery = useQuery({
    queryKey: ['topics'],
    queryFn: listTopics,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  // Normalize group options into simple strings (robust to various backend shapes)
  const groupOptions = React.useMemo(() => {
    const raw = groupsQuery.data ?? [];
    return raw
      .map((g) => {
        if (typeof g === 'string') return g;
        if (g && typeof g === 'object') return g.groupId ?? g.id ?? g.name ?? g[0];
        if (Array.isArray(g)) return g[0];
        return undefined;
      })
      .filter(Boolean);
  }, [groupsQuery.data]);

  // Normalize topics to names
  const topicOptions = React.useMemo(
    () => (topicsQuery.data ?? []).map((t) => t?.name ?? t).filter(Boolean),
    [topicsQuery.data]
  );

  // ----- lag query -----
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
      if (!tsLocal) {
        enqueueSnackbar('Please choose a timestamp first', { variant: 'warning' });
        return;
      }
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

  const canLoad = Boolean(groupId && topic);

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Consumer Groups</Typography>

      <Paper sx={{ p:2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          {/* Consumer Group (dropdown + free typing) */}
          <Autocomplete
            freeSolo
            options={groupOptions}
            value={groupId}
            inputValue={groupInput}
            onChange={(_, v) => { setGroupId(v || ''); setGroupInput(v || ''); }}
            onInputChange={(_, v) => setGroupInput(v)}
            loading={groupsQuery.isFetching}
            loadingText="Loading groups…"
            noOptionsText="No groups"
            renderInput={(params) => (
              <TextField
                {...params}
                label="Group ID"
                size="small"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {groupsQuery.isFetching ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            sx={{ minWidth: 280 }}
          />

          {/* Topic (dropdown + free typing) */}
          <Autocomplete
            freeSolo
            options={topicOptions}
            value={topic}
            inputValue={topicInput}
            onChange={(_, v) => { setTopic(v || ''); setTopicInput(v || ''); }}
            onInputChange={(_, v) => setTopicInput(v)}
            loading={topicsQuery.isFetching}
            loadingText="Loading topics…"
            noOptionsText="No topics"
            renderInput={(params) => (
              <TextField
                {...params}
                label="Topic"
                size="small"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {topicsQuery.isFetching ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
            sx={{ minWidth: 280 }}
          />

          <Button variant="contained" onClick={() => query.refetch()} disabled={!canLoad}>
            Load
          </Button>
          <Button variant={auto ? 'contained' : 'outlined'} onClick={() => setAuto(v => !v)} disabled={!canLoad}>
            Auto 10s
          </Button>
        </Stack>
      </Paper>

      {query.isError && (
        <Alert severity="error">
          {query.error?.message || 'Failed to load lag data'}
        </Alert>
      )}

      {query.data && (
        <Paper sx={{ p:2 }}>
          <Typography variant="subtitle1">Partitions (Lag &amp; Drift)</Typography>
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
                    {typeof p.lag === 'number' ? (
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
              {!query.isFetching && parts.length === 0 && (
                <TableRow><TableCell colSpan={5}>No partitions to display.</TableCell></TableRow>
              )}
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
              <Button variant="outlined" onClick={() => doPreview.mutate()} disabled={!tsLocal || doPreview.isPending}>
                {doPreview.isPending ? 'Preview…' : 'Preview'}
              </Button>
              <Button variant="contained" color="error" onClick={() => setConfirmOpen(true)} disabled={!preview}>
                Confirm Apply
              </Button>
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
          <Button onClick={() => doApply.mutate()} color="error" variant="contained" disabled={!preview || doApply.isPending}>
            {doApply.isPending ? 'Applying…' : 'Apply'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
