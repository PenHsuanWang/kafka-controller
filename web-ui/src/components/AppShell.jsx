import React from 'react';
import { Box, Drawer, Toolbar } from '@mui/material';
import TopBar from './TopBar';
import Sidebar from './Sidebar';
import { WsProvider } from '../ws/WsProvider';

const drawerWidth = 240;

export default function AppShell({ children }) {
  return (
    <WsProvider>
      <Box sx={{ display: 'flex' }}>
        <TopBar drawerWidth={drawerWidth} />
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          <Sidebar />
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
          <Toolbar />
          {children}
        </Box>
      </Box>
    </WsProvider>
  );
}
