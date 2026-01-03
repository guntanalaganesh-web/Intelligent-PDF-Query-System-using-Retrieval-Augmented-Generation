import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DocumentView from './pages/DocumentView';
import ChatInterface from './pages/ChatInterface';
import Upload from './pages/Upload';
import Analytics from './pages/Analytics';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/documents/:documentId" element={<DocumentView />} />
        <Route path="/documents/:documentId/chat" element={<ChatInterface />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Layout>
  );
}

export default App;
