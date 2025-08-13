import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import Dashboard from './pages/Dashboard';
import Groups from './pages/Groups';
import TopicsList from './pages/TopicsList';
import TopicDetail from './pages/TopicDetail';
import Messages from './pages/Messages';
import Settings from './pages/Settings';
import Landing from './pages/Landing';
import Audit from './pages/Audit';
import Requests from './pages/Requests';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/groups" element={<Groups />} />
        <Route path="/topics" element={<TopicsList />} />
        <Route path="/topics/:topic" element={<TopicDetail />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/landing" element={<Landing />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/requests" element={<Requests />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
