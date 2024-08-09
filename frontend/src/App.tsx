// src/App.tsx

// src/App.tsx

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { AuthProvider } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import theme from './theme';
import LoginForm from './components/LoginForm';
import RegistrationForm from './components/RegistrationForm';
import Dashboard from './components/Dashboard';
import PatientProfileForm from './components/PatientProfileForm';
import TrialMatchingResults from './components/TrialMatchingResults';
import Navigation from './components/Navigation';
import ErrorBoundary from './components/ErrorBoundary';

const App: React.FC = () => {
  // Removed socketService usage

  const handleProfileUpdate = () => {
    // You might want to trigger a re-fetch of user data here
    console.log('Profile updated');
  };

  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Router>
            <Navigation />
            <Routes>
              <Route path="/login" element={<LoginForm />} />
              <Route path="/register" element={<RegistrationForm />} />
              <Route path="/" element={<PrivateRoute />}>
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="profile" element={<PatientProfileForm onProfileUpdate={handleProfileUpdate} />} />
                <Route path="trial-matches" element={<TrialMatchingResults />} />
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
