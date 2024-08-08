// src/components/TrialMatchingResults.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Paper, Typography, Button, CircularProgress, 
  List, ListItem, ListItemText, Alert, Box, Pagination
} from '@mui/material';
import api from '../config/api';

// Define interfaces for our data structures
interface Trial {
  nct_id: string;
  title: string;
  brief_summary: string;
  phase: string[];
  status: string;
  compatibility_score: number;
  timestamp: string;
}

interface PaginatedResponse {
  matches: Trial[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// TrialCard component remains the same
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
          <Typography variant="body2">Matched on: {new Date(trial.timestamp).toLocaleString()}</Typography>
        </>
      }
    />
  </ListItem>
);

const TrialMatchingResults: React.FC = () => {
  const [trials, setTrials] = useState<Trial[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchTrials = useCallback(async (pageNum: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get<PaginatedResponse>('/trial-matching/all-matches', {
        params: { page: pageNum, per_page: 10 }
      });
      setTrials(response.data.matches);
      setTotalPages(response.data.total_pages);
    } catch (err) {
      setError('Failed to fetch trials. Please try again.');
      console.error('Error fetching trials:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrials(page);
  }, [fetchTrials, page]);

  const startNewMatching = async () => {
    setIsSearching(true);
    setError(null);
    try {
      await api.post('/trial-matching/start-match');
      checkMatchingStatus();
    } catch (err) {
      setError('Failed to start matching process. Please try again.');
      console.error('Error starting matching process:', err);
      setIsSearching(false);
    }
  };

  const stopSearching = async () => {
    setError(null);
    try {
      await api.post('/trial-matching/stop-match');
      setIsSearching(false);
    } catch (err) {
      setError('Failed to stop matching process. It may stop on its own shortly.');
      console.error('Error stopping matching process:', err);
    }
  };

  const checkMatchingStatus = useCallback(async () => {
    try {
      const response = await api.get('/trial-matching/match-status');
      const { status } = response.data;
      
      if (status === 'in_progress') {
        setTimeout(checkMatchingStatus, 5000); // Check again in 5 seconds
      } else if (status === 'completed') {
        setIsSearching(false);
        fetchTrials(1); // Refresh the trial list from the first page
      } else if (status === 'error') {
        setError('An error occurred during the matching process.');
        setIsSearching(false);
      }
    } catch (err) {
      console.error('Error checking matching status:', err);
      setIsSearching(false);
    }
  }, [fetchTrials]);

  const handlePageChange = (event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  return (
    <Paper style={{ padding: '20px', margin: '20px 0' }}>
      <Typography variant="h5" gutterBottom>Matching Clinical Trials</Typography>
      
      {error && (
        <Alert severity="error" style={{ marginBottom: '20px' }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={startNewMatching}
          disabled={isSearching}
        >
          {isSearching ? 'Searching...' : 'Start New Matching'}
        </Button>
        <Button 
          variant="contained" 
          color="secondary" 
          onClick={stopSearching}
          disabled={!isSearching}
        >
          Stop Searching
        </Button>
        <Button 
          variant="outlined" 
          color="primary" 
          onClick={() => fetchTrials(page)}
          disabled={isSearching}
        >
          Refresh Trials
        </Button>
      </Box>

      {isSearching && (
        <Box sx={{ display: 'flex', justifyContent: 'center', marginBottom: 2 }}>
          <CircularProgress />
        </Box>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <List>
            {trials.map((trial) => (
              <TrialCard key={trial.nct_id} trial={trial} />
            ))}
          </List>
          <Box sx={{ display: 'flex', justifyContent: 'center', marginTop: 2 }}>
            <Pagination 
              count={totalPages} 
              page={page} 
              onChange={handlePageChange} 
              color="primary" 
            />
          </Box>
        </>
      )}

      {trials.length === 0 && !isLoading && !isSearching && (
        <Typography variant="body1">No matching trials found. Try starting a new search.</Typography>
      )}
    </Paper>
  );
};

export default TrialMatchingResults;