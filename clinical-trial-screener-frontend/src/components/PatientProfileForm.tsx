// src/components/PatientProfileForm.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { 
  TextField, 
  Button, 
  Paper, 
  Typography, 
  Checkbox, 
  FormControlLabel, 
  Alert, 
  CircularProgress,
  Grid
} from '@mui/material';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { sanitizeInput } from '../utils/inputSanitizer';
import { handleError } from '../utils/errorHandler';

interface PatientProfileFormProps {
  onProfileUpdate: () => void;
}

interface PatientProfileData {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  medical_conditions: string;
  medications: string;
  consentToContact: boolean;
}

const PatientProfileForm: React.FC<PatientProfileFormProps> = ({ onProfileUpdate }) => {
  const [formData, setFormData] = useState<PatientProfileData>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
    gender: '',
    medical_conditions: '',
    medications: '',
    consentToContact: false
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { token } = useAuth();

  const fetchProfile = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await axios.get('http://localhost:5000/api/patient/profile', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormData(prevState => ({
        ...prevState,
        ...response.data,
        medical_conditions: Array.isArray(response.data.medical_conditions) 
          ? response.data.medical_conditions.join(', ') 
          : response.data.medical_conditions || '',
        medications: Array.isArray(response.data.medications) 
          ? response.data.medications.join(', ') 
          : response.data.medications || '',
      }));
    } catch (err) {
      const errorMessage = handleError(err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : sanitizeInput(value)
    }));
  };

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsLoading(true);

    try {
      const dataToSubmit = {
        ...formData,
        medical_conditions: formData.medical_conditions.split(',').map(condition => condition.trim()),
        medications: formData.medications.split(',').map(medication => medication.trim())
      };

      await axios.put('http://localhost:5000/api/patient/profile', dataToSubmit, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Profile updated successfully');
      onProfileUpdate();
    } catch (err) {
      const errorMessage = handleError(err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [formData, token, onProfileUpdate]);

  if (isLoading) {
    return (
      <Paper style={{ padding: '20px', maxWidth: '500px', margin: '0 auto', textAlign: 'center' }}>
        <CircularProgress />
        <Typography>Loading profile data...</Typography>
      </Paper>
    );
  }

  return (
    <Paper style={{ padding: '20px', maxWidth: '500px', margin: '0 auto' }}>
      <Typography variant="h5" gutterBottom>Patient Profile</Typography>
      {error && <Alert severity="error" style={{ marginBottom: '20px' }}>{error}</Alert>}
      {success && <Alert severity="success" style={{ marginBottom: '20px' }}>{success}</Alert>}
      <form onSubmit={handleSubmit}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="First Name"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              required
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Last Name"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              required
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Date of Birth"
              name="date_of_birth"
              type="date"
              value={formData.date_of_birth}
              onChange={handleChange}
              InputLabelProps={{
                shrink: true,
              }}
              required
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Gender"
              name="gender"
              value={formData.gender}
              onChange={handleChange}
              required
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Medical Conditions (comma-separated)"
              name="medical_conditions"
              multiline
              rows={4}
              value={formData.medical_conditions}
              onChange={handleChange}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Medications (comma-separated)"
              name="medications"
              multiline
              rows={4}
              value={formData.medications}
              onChange={handleChange}
            />
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={formData.consentToContact}
                  onChange={handleChange}
                  name="consentToContact"
                />
              }
              label="I consent to be contacted about matching clinical trials"
            />
          </Grid>
          <Grid item xs={12}>
            <Button 
              type="submit" 
              variant="contained" 
              color="primary" 
              disabled={isLoading}
              fullWidth
            >
              {isLoading ? 'Saving...' : 'Save Profile'}
            </Button>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
};

export default PatientProfileForm;