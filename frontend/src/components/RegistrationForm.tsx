// src/components/RegistrationForm.tsx

import React, { useState, useCallback } from 'react';
import { TextField, Button, Paper, Typography } from '@mui/material';
import { styled } from '@mui/system';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { sanitizeInput, validateEmail, validatePassword } from '../utils/inputSanitizer';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  maxWidth: '400px',
  margin: '0 auto',
  marginTop: theme.spacing(8),
  backgroundColor: '#f0f4f7',
}));

const StyledForm = styled('form')(({ theme }) => ({
  width: '100%',
  marginTop: theme.spacing(1),
}));

const StyledButton = styled(Button)(({ theme }) => ({
  margin: theme.spacing(3, 0, 2),
  backgroundColor: '#1976d2',
  color: 'white',
  '&:hover': {
    backgroundColor: '#115293',
  },
}));

const ErrorText = styled(Typography)(({ theme }) => ({
  color: theme.palette.error.main,
  marginTop: theme.spacing(2),
}));

const RegistrationForm: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: ''
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (!validateEmail(formData.email)) {
        throw new Error('Please enter a valid email address.');
      }

      const passwordValidation = validatePassword(formData.password);
      if (!passwordValidation.isValid) {
        throw new Error(passwordValidation.message);
      }

      if (formData.password !== formData.confirmPassword) {
        throw new Error('Passwords do not match');
      }

      const sanitizedData = {
        email: sanitizeInput(formData.email),
        password: formData.password, // Don't sanitize password
        firstName: sanitizeInput(formData.firstName),
        lastName: sanitizeInput(formData.lastName)
      };

      const response = await axios.post('http://localhost:5000/api/auth/register', sanitizedData);
      console.log('Registration successful', response.data);
      navigate('/login');
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.message || 'An error occurred during registration.');
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
      console.error('Registration error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [formData, navigate]);

  return (
    <StyledPaper>
      <Typography variant="h5">Register</Typography>
      <StyledForm onSubmit={handleSubmit}>
        <TextField
          fullWidth
          margin="normal"
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          required
          inputProps={{
            maxLength: 255,
          }}
        />
        <TextField
          fullWidth
          margin="normal"
          label="Password"
          name="password"
          type="password"
          value={formData.password}
          onChange={handleChange}
          required
          inputProps={{
            minLength: 8,
            maxLength: 128,
            autoComplete: "new-password"
          }}
        />
        <TextField
          fullWidth
          margin="normal"
          label="Confirm Password"
          name="confirmPassword"
          type="password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          inputProps={{
            minLength: 8,
            maxLength: 128,
            autoComplete: "new-password"
          }}
        />
        <TextField
          fullWidth
          margin="normal"
          label="First Name"
          name="firstName"
          value={formData.firstName}
          onChange={handleChange}
          required
        />
        <TextField
          fullWidth
          margin="normal"
          label="Last Name"
          name="lastName"
          value={formData.lastName}
          onChange={handleChange}
          required
        />
        <StyledButton type="submit" variant="contained" color="primary" disabled={isLoading}>
          {isLoading ? 'Registering...' : 'Register'}
        </StyledButton>
      </StyledForm>
      {error && <ErrorText>{error}</ErrorText>}
    </StyledPaper>
  );
};

export default RegistrationForm;