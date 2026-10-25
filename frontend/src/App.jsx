import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import NewDealModal from './components/NewDealModal';
import ProfileModal from './components/ProfileModal';
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
import DealWorkspacePage from './pages/DealWorkspacePage';
import InvitePage from './pages/InvitePage';

import AdminAuthorizationModal from './components/AdminAuthorizationModal';

function AppContent() {
  const { user, loading } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('signin');
  const [newDealModalOpen, setNewDealModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [adminAuthModalOpen, setAdminAuthModalOpen] = useState(false);

  function handleOpenAuth(mode = 'signin') {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  }

  function handleOpenNewDeal() {
    if (!user) {
      handleOpenAuth('signin');
      return;
    }
    setNewDealModalOpen(true);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-400 text-xs font-medium animate-pulse">Loading Legalbandu...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        onOpenAuth={handleOpenAuth}
        onOpenNewDeal={handleOpenNewDeal}
        onOpenProfile={() => setProfileModalOpen(true)}
        onOpenAdminAuth={() => setAdminAuthModalOpen(true)}
      />

      <main className="flex-1">
        <Routes>
          <Route
            path="/"
            element={
              user ? (
                <Navigate to="/dashboard" replace />
              ) : (
                <LandingPage
                  onOpenAuth={handleOpenAuth}
                  onOpenNewDeal={handleOpenNewDeal}
                />
              )
            }
          />

          <Route
            path="/dashboard"
            element={
              user ? (
                <DashboardPage onOpenNewDeal={handleOpenNewDeal} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />

          <Route
            path="/deal/:dealId"
            element={
              user ? (
                <DealWorkspacePage onOpenAdminAuth={() => setAdminAuthModalOpen(true)} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />

          <Route
            path="/invite/:token"
            element={<InvitePage onOpenAuth={handleOpenAuth} />}
          />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Global Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />

      <NewDealModal
        isOpen={newDealModalOpen}
        onClose={() => setNewDealModalOpen(false)}
      />

      <ProfileModal
        isOpen={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
      />

      <AdminAuthorizationModal
        isOpen={adminAuthModalOpen}
        onClose={() => setAdminAuthModalOpen(false)}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}
