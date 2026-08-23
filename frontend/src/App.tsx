import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { AppNavbar } from './components/AppNavbar';
import { QAPanel } from './components/QAPanel';

import { LandingPage } from './pages/LandingPage';
import { StartScreen } from './pages/StartScreen';
import { SkillsScreen } from './pages/SkillsScreen';
import { TargetRoleScreen } from './pages/TargetRoleScreen';
import { PathScreen } from './pages/PathScreen';
import { DashboardScreen } from './pages/DashboardScreen';
import { CelebrationScreen } from './pages/CelebrationScreen';

// Route Guard Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { sessionId } = useApp();
  if (!sessionId) {
    return <Navigate to="/start" replace />;
  }
  return <>{children}</>;
};

// In-App Container with Navbar and QAPanel
const AppContainer: React.FC = () => {
  const location = useLocation();
  const isLandingPage = location.pathname === '/';

  return (
    <div className="min-h-screen bg-paper text-ink">
      {!isLandingPage && <AppNavbar />}

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/start" element={<StartScreen />} />
        <Route path="/skills" element={<SkillsScreen />} />
        <Route
          path="/target-role"
          element={
            <ProtectedRoute>
              <TargetRoleScreen />
            </ProtectedRoute>
          }
        />
        <Route
          path="/path"
          element={
            <ProtectedRoute>
              <PathScreen />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardScreen />
            </ProtectedRoute>
          }
        />
        <Route
          path="/celebration"
          element={
            <ProtectedRoute>
              <CelebrationScreen />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {!isLandingPage && <QAPanel />}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppContainer />
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
