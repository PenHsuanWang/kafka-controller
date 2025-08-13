import React from 'react';
import { AppBar, Toolbar, Typography, Box, IconButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import LightModeIcon from '@mui/icons-material/LightMode';

export default function TopBar({ drawerWidth }) {
  return (
    <AppBar position="fixed" sx={{ width: `calc(100% - ${drawerWidth}px)`, ml: `${drawerWidth}px` }}>
      <Toolbar>
        <IconButton color="inherit" edge="start" sx={{ mr: 2 }}>
          <MenuIcon />
        </IconButton>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Kafka Cluster Admin
        </Typography>
        <Box>
          <IconButton color="inherit" aria-label="theme">
            <LightModeIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
