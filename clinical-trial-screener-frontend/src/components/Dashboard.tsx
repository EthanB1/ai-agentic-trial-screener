// src/components/Dashboard.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Paper, Typography, Grid, Card, CardContent, 
  Button, CircularProgress, List, ListItem, ListItemText, Alert
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import api from '../config/api';
import { handleError } from '../utils/errorHandler';

interface PatientInfo {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  medical_conditions: string[];
  medications: string[];
}

interface Trial {
  nct_id: string;
  title: string;
  brief_summary: string;
  phase: string[];
  status: string;
  compatibility_score: number;
}

const TrialCard: React.FC<{ trial: Trial }> = ({ trial }) => (
  <ListItem>
    <ListItemText
      primary={`Trial ${trial.nct_id}: ${trial.title}`}
      secondary={
        <>
          <Typography variant="body2">{trial.brief_summary}</Typography>
          <Typography variant="body2">Phase: {trial.phase.join(', ')}</Typography>
          <Typography variant="body2">Status: {trial.status}</Typography>
          <Typography variant="body2">Compatibility: {trial.compatibility_score}%</Typography>
        </>
      }
    />
  </ListItem>
);

const Dashboard: React.FC = () => {
  const [patientInfo, setPatientInfo] = useState<PatientInfo | null>(null);
  const [recentMatches, setRecentMatches] = useState<Trial[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [patientResponse, matchesResponse] = await Promise.all([
        api.get<PatientInfo>('/patient/profile'),
        api.get<Trial[]>('/trial-matching/matches')  // This endpoint should return recent matches
      ]);
      setPatientInfo(patientResponse.data);
      setRecentMatches(matchesResponse.data);
    } catch (err) {
      const errorMessage = handleError(err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (isLoading) {
    return (
      <Grid container justifyContent="center" alignItems="center" style={{ height: '100vh' }}>
        <CircularProgress />
      </Grid>
    );
  }

  return (
    <Grid container spacing={3}>
      {error && (
        <Grid item xs={12}>
          <Alert severity="error">{error}</Alert>
        </Grid>
      )}
      <Grid item xs={12} md={6}>
        <Paper style={{ padding: '20px' }}>
          <Typography variant="h6" gutterBottom>Patient Profile</Typography>
          {patientInfo ? (
            <>
              <Typography>Name: {patientInfo.first_name} {patientInfo.last_name}</Typography>
              <Typography>Date of Birth: {patientInfo.date_of_birth}</Typography>
              <Typography>Gender: {patientInfo.gender}</Typography>
              <Typography>
                Medical Conditions: {patientInfo.medical_conditions.join(', ')}
              </Typography>
              <Typography>
                Medications: {patientInfo.medications.join(', ')}
              </Typography>
              <Button 
                component={RouterLink} 
                to="/profile" 
                variant="contained" 
                color="primary" 
                style={{ marginTop: '10px' }}
              >
                Edit Profile
              </Button>
            </>
          ) : (
            <Typography>No profile information available. Please update your profile.</Typography>
          )}
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Recent Trial Matches</Typography>
            {recentMatches.length > 0 ? (
              <List>
                {recentMatches.map((match) => (
                  <TrialCard key={match.nct_id} trial={match} />
                ))}
              </List>
            ) : (
              <Typography>No recent matches found. This may be due to an incomplete profile or no matching trials at the moment.</Typography>
            )}
            <Button 
              component={RouterLink} 
              to="/trial-matches" 
              variant="contained" 
              color="secondary" 
              style={{ marginTop: '10px' }}
            >
              View All Matches
            </Button>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default Dashboard;