import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { listTopics } from '../api/topics';
import { Paper, Table, TableHead, TableRow, TableCell, TableBody, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';

export default function TopicsList() {
  const { data } = useQuery({ queryKey: ['topics'], queryFn: listTopics, refetchOnWindowFocus: true });
  const nav = useNavigate();
  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Topics</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Partitions</TableCell>
            <TableCell>RF</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(data ?? []).map(t => (
            <TableRow key={t.name} hover onClick={() => nav(`/topics/${encodeURIComponent(t.name)}`)} sx={{ cursor: 'pointer' }}>
              <TableCell>{t.name}</TableCell>
              <TableCell>{t.partitions}</TableCell>
              <TableCell>{t.replicationFactor}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}
