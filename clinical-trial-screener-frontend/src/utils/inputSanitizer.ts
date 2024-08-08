// src/utils/inputSanitizer.ts

import DOMPurify from 'dompurify';

/**
 * Sanitizes input to prevent XSS attacks and other malicious inputs.
 * @param input - The input string to sanitize
 * @returns The sanitized input string
 */
export const sanitizeInput = (input: string): string => {
  // First, use DOMPurify to remove any potentially malicious HTML
  const sanitizedInput = DOMPurify.sanitize(input);
  
  // Then, remove any remaining special characters except for common punctuation
  return sanitizedInput.replace(/[^\w\s.,;:!?()-]/gi, '');
};

/**
 * Sanitizes an object's string properties recursively
 * @param obj - The object to sanitize
 * @returns A new object with all string properties sanitized
 */
export const sanitizeObject = <T extends object>(obj: T): T => {
  const sanitizedObj = { ...obj };
  for (const [key, value] of Object.entries(sanitizedObj)) {
    if (typeof value === 'string') {
      sanitizedObj[key as keyof T] = sanitizeInput(value) as T[keyof T];
    } else if (typeof value === 'object' && value !== null) {
      sanitizedObj[key as keyof T] = sanitizeObject(value) as T[keyof T];
    }
  }
  return sanitizedObj;
};

/**
 * Validates an email address
 * @param email - The email address to validate
 * @returns True if the email is valid, false otherwise
 */
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
  return emailRegex.test(email);
};

/**
 * Validates a password for strength
 * @param password - The password to validate
 * @returns An object with a boolean indicating if the password is valid and a message
 */
export const validatePassword = (password: string): { isValid: boolean; message: string } => {
  if (password.length < 8) {
    return { isValid: false, message: 'Password must be at least 8 characters long' };
  }
  if (!/[A-Z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one uppercase letter' };
  }
  if (!/[a-z]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one lowercase letter' };
  }
  if (!/[0-9]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one number' };
  }
  if (!/[!@#$%^&*]/.test(password)) {
    return { isValid: false, message: 'Password must contain at least one special character (!@#$%^&*)' };
  }
  return { isValid: true, message: 'Password is strong' };
};