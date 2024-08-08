// src/utils/errorHandler.ts

import { AxiosError } from 'axios';

export const handleError = (error: unknown): string => {
  if (error instanceof AxiosError) {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Server error:', error.response.data);
      return `Server error: ${error.response.data.message || 'Unknown error'}`;
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
      return 'No response received from server. Please try again later.';
    }
  }
  // Something happened in setting up the request that triggered an Error
  console.error('Error:', error);
  return 'An unexpected error occurred. Please try again.';
};