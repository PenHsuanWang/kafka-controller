import React from 'react';
import {
  Paper, Stack, Typography, TextField, Button, RadioGroup,
  FormControlLabel, Radio, Table, TableHead, TableRow, TableCell, TableBody, Alert,
  Autocomplete, CircularProgress, MenuItem
} from '@mui/material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getByOffset, getFromTimestamp } from '../api/messages';
import { listTopics, getTopic } from '../api/topics';
import { toIsoUtcZ } from '../utils/datetime';
import { b64ToUtf8 } from '../utils/base64';

function decodeMaybeB64(row, b64Field, rawField) {
  // Prefer explicit base64 fields; fallback to raw fields for backward compatibility
  const b64 = row[b64Field];
  if (b64 != null) return b64ToUtf8(b64) ?? '(binary)';
  const raw = row[rawField];
  if (typeof raw === 'string') {
    try { return b64ToUtf8(raw) ?? raw; } catch { return raw; }
  }
  return '(binary)';
}

export default function Messages() {
  // ---- form state
  const [topic, setTopic] = React.useState('');     // string topic name from dropdown
  const [partition, setPartition] = React.useState(''); // string for UI; convert to number on fetch
  const [mode, setMode] = React.useState('offset');
  const [offset, setOffset] = React.useState(0);
  const [ts, setTs] = React.useState('');
  const [limit, setLimit] = React.useState(50);
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState(null);

  // ---- topics list for dropdown
  const topicsQ = useQuery({
    queryKey: ['topics', 'all'],
    queryFn: () => listTopics(),
    staleTime: 15_000,
  });
  const topicNames = (topicsQ.data ?? []).map(t => t.name);

  // reset partition when topic changes
  React.useEffect(() => { setPartition(''); }, [topic]);

  // ---- topic detail to get partitions for selected topic
  const topicDetailQ = useQuery({
    queryKey: ['topic-detail', topic],
    queryFn: () => getTopic(topic),
    enabled: !!topic,
    staleTime: 10_000,
  });
  const partitions = topicDetailQ.data?.partitions?.map(p => p.id) ?? [];

  // choose a default partition when available
  React.useEffect(() => {
    if (!partition && partitions.length > 0) {
      setPartition(String(partitions[0]));
    }
  }, [partitions, partition]);

  // ---- manual fetch
  const fetcher = useMutation({
    mutationFn: async () => {
      setError(null);
      if (!topic) throw new Error('Topic is required');
      if (partition === '') throw new Error('Partition is required');

      const pnum = Number(partition);
      const lim = Number(limit) || 50;

      if (mode === 'offset') {
        const res = await getByOffset(topic, pnum, Number(offset) || 0, lim);
        setRows(res || []);
      } else {
        const iso = ts && ts.includes('T') ? toIsoUtcZ(ts) : ts;
        if (!iso) throw new Error('Timestamp is required in timestamp mode');
        const res = await getFromTimestamp(topic, pnum, iso, lim);
        setRows(res || []);
      }
    },
    onError: (e) => setError(e.message || String(e)),
  });

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Messages</Typography>

      <Paper sx={{ p:2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
          {/* Topic dropdown (string options) */}
          <Autocomplete
            options={topicNames}
            value={topic || null}
            onChange={(_, v) => setTopic(v || '')}
            loading={topicsQ.isLoading}
            sx={{ minWidth: 280 }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Topic"
                size="small"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {topicsQ.isLoading ? <CircularProgress size={18} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
                helperText="Select a topic"
              />
            )}
          />

          {/* Partition dropdown (based on selected topic) */}
          <TextField
            select
            size="small"
            label="Partition"
            value={partition}
            onChange={(e) => setPartition(e.target.value)}
            sx={{ minWidth: 160 }}
            disabled={!topic || topicDetailQ.isLoading}
            helperText={!topic ? 'Choose topic first' : 'Select partition'}
          >
            {partitions.map(pid => (
              <MenuItem key={pid} value={String(pid)}>{pid}</MenuItem>
            ))}
          </TextField>

          {/* Limit */}
          <TextField
            label="Limit"
            size="small"
            type="number"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            sx={{ width: 120 }}
            inputProps={{ min: 1, max: 1000 }}
          />
        </Stack>

        <RadioGroup row value={mode} onChange={(e) => setMode(e.target.value)}>
          <FormControlLabel value="offset" control={<Radio />} label="By Offset" />
          <FormControlLabel value="timestamp" control={<Radio />} label="By Timestamp" />
        </RadioGroup>

        {mode === 'offset' ? (
          <TextField
            label="Offset"
            size="small"
            type="number"
            value={offset}
            onChange={e => setOffset(Number(e.target.value))}
            sx={{ width: 220 }}
            helperText="Start reading at this offset"
          />
        ) : (
          <TextField
            label="Timestamp"
            type="datetime-local"
            size="small"
            value={ts}
            onChange={e => setTs(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 260 }}
            helperText="If set, takes precedence over offset"
          />
        )}

        <Stack sx={{ mt:2 }}>
          <Button variant="contained" onClick={() => fetcher.mutate()} disabled={fetcher.isPending}>
            {fetcher.isPending ? 'Loading…' : 'Fetch'}
          </Button>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mt:2 }}>
            {error}
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p:2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Partition</TableCell>
              <TableCell>Offset</TableCell>
              <TableCell>Timestamp</TableCell>
              <TableCell>Key</TableCell>
              <TableCell>Value (utf-8 preview)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r, i) => (
              <TableRow key={`${r.partition}-${r.offset}-${i}`}>
                <TableCell>{i + 1}</TableCell>
                <TableCell>{r.partition}</TableCell>
                <TableCell>{r.offset}</TableCell>
                <TableCell>{r.timestampIso ?? (r.timestamp ? new Date(r.timestamp).toISOString() : '')}</TableCell>
                <TableCell>{decodeMaybeB64(r, 'keyB64', 'key')}</TableCell>
                <TableCell>{decodeMaybeB64(r, 'valueB64', 'value')}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
