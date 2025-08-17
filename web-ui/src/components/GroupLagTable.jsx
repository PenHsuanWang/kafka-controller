import React from 'react';
import {
  Table, TableHead, TableRow, TableCell, TableBody, IconButton, Tooltip, Chip,
} from '@mui/material';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import HistoryToggleOffOutlinedIcon from '@mui/icons-material/HistoryToggleOffOutlined';
import { fmtIsoShort } from '../utils/datetime';

export default function GroupLagTable({ parts = [], onPeekMessages, onSeedReset }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>#</TableCell>
          <TableCell>Committed / End</TableCell>
          <TableCell>Lag</TableCell>
          <TableCell>End TS</TableCell>
          <TableCell>LastRec TS</TableCell>
          <TableCell>Time Lag</TableCell>
          <TableCell align="right">Actions</TableCell>
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
            <TableCell>{Number.isFinite(p.timeLagSec) ? `${p.timeLagSec}s` : '—'}</TableCell>
            <TableCell align="right">
              {onPeekMessages && (
                <Tooltip title="Peek messages">
                  <IconButton size="small" onClick={() => onPeekMessages(p.partition)}>
                    <ArticleOutlinedIcon fontSize="inherit" />
                  </IconButton>
                </Tooltip>
              )}
              {onSeedReset && (
                <Tooltip title="Use partition for reset">
                  <IconButton size="small" onClick={() => onSeedReset(p.partition)}>
                    <HistoryToggleOffOutlinedIcon fontSize="inherit" />
                  </IconButton>
                </Tooltip>
              )}
            </TableCell>
          </TableRow>
        ))}
        {parts.length === 0 && (
          <TableRow><TableCell colSpan={7}>No partitions to display.</TableCell></TableRow>
        )}
      </TableBody>
    </Table>
  );
}
