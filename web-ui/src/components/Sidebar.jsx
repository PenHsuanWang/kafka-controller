import React from 'react';
import { List, ListItemButton, ListItemIcon, ListItemText, Divider } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import GroupsIcon from '@mui/icons-material/Groups';
import TopicIcon from '@mui/icons-material/Topic';
import MessageIcon from '@mui/icons-material/Message';
import StorageIcon from '@mui/icons-material/Storage';
import PolicyIcon from '@mui/icons-material/Policy';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import SettingsIcon from '@mui/icons-material/Settings';
import { useNavigate, useLocation } from 'react-router-dom';

const items = [
  { to: '/', label: 'Dashboard', icon: <DashboardIcon /> },
  { to: '/groups', label: 'Groups', icon: <GroupsIcon /> },
  { to: '/topics', label: 'Topics', icon: <TopicIcon /> },
  { to: '/messages', label: 'Messages', icon: <MessageIcon /> },
  { to: '/landing', label: 'Landing', icon: <StorageIcon /> },
  { to: '/audit', label: 'Audit', icon: <PolicyIcon /> },
  { to: '/requests', label: 'Requests', icon: <VerifiedUserIcon /> },
];

export default function Sidebar() {
  const nav = useNavigate();
  const loc = useLocation();
  return (
    <>
      <List>
        {items.map((it) => (
          <ListItemButton key={it.to} selected={loc.pathname === it.to} onClick={() => nav(it.to)}>
            <ListItemIcon>{it.icon}</ListItemIcon>
            <ListItemText primary={it.label} />
          </ListItemButton>
        ))}
      </List>
      <Divider />
      <List>
        <ListItemButton onClick={() => nav('/settings')}>
          <ListItemIcon><SettingsIcon /></ListItemIcon>
          <ListItemText primary="Settings" />
        </ListItemButton>
      </List>
    </>
  );
}
