import React from 'react';
import { Paper, Stack, Typography, TextField, Button, RadioGroup, FormControlLabel, Radio, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';
import { useMutation } from '@tanstack/react-query';
import { getByOffset, getFromTimestamp } from '../api/messages';
import { toIsoUtcZ } from '../utils/datetime';
import { b64ToUtf8 } from '../utils/base64';

export default function Messages() {
  const [topic, setTopic] = React.useState('demo');
  const [partition, setPartition] = React.useState(0);
  const [mode, setMode] = React.useState('offset');
  const [offset, setOffset] = React.useState(0);
  const [ts, setTs] = React.useState('');
  const [limit, setLimit] = React.useState(50);
  const [rows, setRows] = React.useState([]);

  const fetcher = useMutation({
    mutationFn: async () => {
      if (mode === 'offset') {
        const res = await getByOffset(topic, partition, offset, limit);
        setRows(res);
      } else {
        const res = await getFromTimestamp(topic, partition, ts.includes('T') ? toIsoUtcZ(ts) : ts, limit);
        setRows(res);
      }
    }
  });

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Messages</Typography>
      <Paper sx={{ p:2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField label="Topic" size="small" value={topic} onChange={e => setTopic(e.target.value)} />
          <TextField label="Partition" size="small" type="number" value={partition} onChange={e => setPartition(Number(e.target.value))} />
          <TextField label="Limit" size="small" type="number" value={limit} onChange={e => setLimit(Number(e.target.value))} />
        </Stack>
        <RadioGroup row value={mode} onChange={(e) => setMode(e.target.value)}>
          <FormControlLabel value="offset" control={<Radio />} label="By Offset" />
          <FormControlLabel value="timestamp" control={<Radio />} label="By Timestamp" />
        </RadioGroup>
        {mode === 'offset' ? (
          <TextField label="Offset" size="small" type="number" value={offset} onChange={e => setOffset(Number(e.target.value))} />
        ) : (
          <TextField label="Timestamp" type="datetime-local" size="small" value={ts} onChange={e => setTs(e.target.value)} InputLabelProps={{ shrink: true }} />
        )}
        <Stack sx={{ mt:2 }}>
          <Button variant="contained" onClick={() => fetcher.mutate()}>Fetch</Button>
        </Stack>
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
              <TableRow key={`${r.partition}-${r.offset}`}>
                <TableCell>{i+1}</TableCell>
                <TableCell>{r.partition}</TableCell>
                <TableCell>{r.offset}</TableCell>
                <TableCell>{new Date(r.timestamp).toISOString()}</TableCell>
                <TableCell>{b64ToUtf8(r.key) ?? '(binary)'}</TableCell>
                <TableCell>{b64ToUtf8(r.value) ?? '(binary)'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
