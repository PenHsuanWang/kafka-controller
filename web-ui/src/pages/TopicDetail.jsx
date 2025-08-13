import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getTopic } from '../api/topics';
import { Paper, Table, TableHead, TableRow, TableCell, TableBody, Stack, Typography } from '@mui/material';

export default function TopicDetail() {
  const { topic = '' } = useParams();
  const { data } = useQuery({ queryKey: ['topic', topic], queryFn: () => getTopic(topic), enabled: !!topic });

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Topic: {topic}</Typography>
      <Paper sx={{ p:2 }}>
        <Typography variant="subtitle1">Partitions</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Leader</TableCell>
              <TableCell>ISR</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>End</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.partitions.map(p => (
              <TableRow key={p.id}>
                <TableCell>{p.id}</TableCell>
                <TableCell>{p.leader ?? '-'}</TableCell>
                <TableCell>[{p.isr.join(', ')}]</TableCell>
                <TableCell>{p.startOffset ?? '-'}</TableCell>
                <TableCell>{p.endOffset ?? '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
