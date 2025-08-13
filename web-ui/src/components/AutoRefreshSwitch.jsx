import React from 'react';
import { FormControlLabel, Switch } from '@mui/material';

export default function AutoRefreshSwitch({ value, onChange }) {
  return (
    <FormControlLabel control={<Switch checked={value} onChange={(e) => onChange(e.target.checked)} />} label="Auto 10s" />
  );
}
